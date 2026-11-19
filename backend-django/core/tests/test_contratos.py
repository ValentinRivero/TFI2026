import pytest
from rest_framework import status

from core.models import (
    Cancha,
    Complejo,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoUsuario,
    LogAuditoria,
    TipoEventoAuditoria,
)

URL = '/api/contratos/'


def _datos_alta(propietario, **cambios):
    datos = {
        'propietario': propietario.id,
        'nombre': 'Complejo Nuevo',
        'direccion': 'Calle Los Ceibos 900, Goya',
        'latitud': '-29.143000',
        'longitud': '-59.265000',
        'telefono_contacto': '3777 000150',
    }
    datos.update(cambios)
    return datos


class TestListadoDeContratos:
    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno'])
    def test_roles_sin_permiso_reciben_403(self, request, cliente_de, fixture_usuario):
        usuario = request.getfixturevalue(fixture_usuario)

        assert cliente_de(usuario).get(URL).status_code == status.HTTP_403_FORBIDDEN

    def test_superadmin_ve_todos_los_estados_con_el_propietario(
        self, superadmin, dueno, crear_complejo, cliente_de,
    ):
        for estado in EstadoContrato:
            crear_complejo(dueno, f'Complejo {estado.label}', estado_contrato=estado)

        respuesta = cliente_de(superadmin).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['count'] == 4
        contrato = respuesta.json()['results'][0]
        assert contrato['propietario'] == {
            'id': dueno.id, 'nombre_completo': dueno.nombre_completo, 'email': dueno.email,
            'estado': EstadoUsuario.ACTIVO, 'estado_nombre': 'Activo',
        }
        assert 'estado_contrato_nombre' in contrato

    def test_no_lista_complejos_con_baja_logica_del_registro(self, superadmin, complejo, cliente_de):
        complejo.desactivar()

        assert cliente_de(superadmin).get(URL).json()['count'] == 0

    def test_filtra_por_estado_de_contrato(self, superadmin, dueno, crear_complejo, cliente_de):
        suspendido = crear_complejo(dueno, 'Suspendido', estado_contrato=EstadoContrato.SUSPENDIDO)
        crear_complejo(dueno, 'Activo', estado_contrato=EstadoContrato.ACTIVO)
        de_baja = crear_complejo(dueno, 'De Baja', estado_contrato=EstadoContrato.BAJA)
        cliente = cliente_de(superadmin)

        suspendidos = cliente.get(URL, {'estado_contrato': EstadoContrato.SUSPENDIDO}).json()['results']
        bajas = cliente.get(URL, {'estado_contrato': EstadoContrato.BAJA}).json()['results']

        assert [contrato['id'] for contrato in suspendidos] == [suspendido.id]
        assert [contrato['id'] for contrato in bajas] == [de_baja.id]

    def test_estado_de_contrato_invalido_responde_400(self, superadmin, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'estado_contrato': 7})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado_contrato' in respuesta.json()['detail']


    def test_deja_a_la_vista_un_contrato_activo_con_titular_suspendido(
        self, superadmin, dueno, otro_dueno, complejo, complejo_ajeno, cliente_de,
    ):
        dueno.estado = EstadoUsuario.SUSPENDIDO
        dueno.save(update_fields=['estado'])

        resultados = cliente_de(superadmin).get(URL, {
            'estado_contrato': EstadoContrato.ACTIVO, 'estado_propietario': EstadoUsuario.SUSPENDIDO,
        }).json()['results']

        assert [contrato['id'] for contrato in resultados] == [complejo.id]
        assert resultados[0]['propietario']['estado_nombre'] == 'Suspendido'

    def test_busca_sin_distinguir_tildes_ni_mayusculas(self, superadmin, dueno, crear_complejo, cliente_de):
        timbos = crear_complejo(dueno, 'Polideportivo Los Timbós')
        crear_complejo(dueno, 'Otro Complejo')
        cliente = cliente_de(superadmin)

        for termino in ('timbos', 'TIMBÓS', 'los timb'):
            resultados = cliente.get(URL, {'search': termino}).json()['results']
            assert [contrato['id'] for contrato in resultados] == [timbos.id], termino


class TestDetalleDeContrato:
    def test_superadmin_consulta_un_contrato(self, superadmin, dueno, complejo, cliente_de):
        respuesta = cliente_de(superadmin).get(f'{URL}{complejo.id}/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['id'] == complejo.id
        assert respuesta.json()['propietario']['id'] == dueno.id

    def test_dueno_no_consulta_contratos(self, dueno, complejo, cliente_de):
        assert cliente_de(dueno).get(f'{URL}{complejo.id}/').status_code == status.HTTP_403_FORBIDDEN

    def test_complejo_inexistente_o_con_baja_logica_responde_404(self, superadmin, complejo, cliente_de):
        complejo.desactivar()
        cliente = cliente_de(superadmin)

        assert cliente.get(f'{URL}{complejo.id}/').status_code == status.HTTP_404_NOT_FOUND
        assert cliente.get(f'{URL}999999/').status_code == status.HTTP_404_NOT_FOUND


class TestAltaDeContrato:
    def test_superadmin_da_de_alta_un_complejo_pendiente(self, superadmin, dueno, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, _datos_alta(dueno), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        complejo = Complejo.objects.get(nombre='Complejo Nuevo')
        assert complejo.propietario == dueno
        assert complejo.estado_contrato == EstadoContrato.PENDIENTE
        assert complejo.horas_limite_cancelacion == 4
        assert respuesta.json()['estado_contrato_nombre'] == 'Pendiente'

    def test_puede_nacer_activo(self, superadmin, dueno, cliente, cliente_de):
        respuesta = cliente_de(superadmin).post(
            URL, _datos_alta(dueno, estado_contrato=EstadoContrato.ACTIVO), format='json',
        )

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert cliente.get(f'/api/complejos/{respuesta.json()["id"]}/').status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('estado', [EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA])
    def test_no_puede_nacer_suspendido_ni_de_baja(self, superadmin, dueno, cliente_de, estado):
        respuesta = cliente_de(superadmin).post(URL, _datos_alta(dueno, estado_contrato=estado), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_el_alta_queda_auditada_en_tabla_y_archivo(self, superadmin, dueno, cliente_de, log_seguridad):
        cliente_de(superadmin).post(URL, _datos_alta(dueno), format='json')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONTRATO)
        assert log.usuario == superadmin
        assert log.complejo == Complejo.objects.get(nombre='Complejo Nuevo')
        assert f'id {dueno.id}' in log.detalle
        assert dueno.email not in log.detalle
        assert 'evento=CAMBIO_CONTRATO' in log_seguridad.text

    @pytest.mark.parametrize('fixture_propietario', ['jugador', 'operador', 'superadmin'])
    def test_el_propietario_debe_ser_dueno(self, request, superadmin, cliente_de, fixture_propietario):
        propietario = request.getfixturevalue(fixture_propietario)

        respuesta = cliente_de(superadmin).post(URL, _datos_alta(propietario), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'propietario' in respuesta.json()['detail']

    @pytest.mark.parametrize('estado', [EstadoUsuario.SUSPENDIDO, EstadoUsuario.BAJA])
    def test_el_propietario_debe_estar_activo(self, superadmin, dueno, cliente_de, estado):
        dueno.estado = estado
        dueno.save(update_fields=['estado'])

        respuesta = cliente_de(superadmin).post(URL, _datos_alta(dueno), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_sanitiza_los_textos(self, superadmin, dueno, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, _datos_alta(
            dueno, nombre='<script>alert(1)</script>La Cancha', info_sena='<b>Seña</b> del 30%',
        ), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        complejo = Complejo.objects.get(id=respuesta.json()['id'])
        assert complejo.nombre == 'La Cancha'
        assert complejo.info_sena == 'Seña del 30%'

    @pytest.mark.parametrize('campo, valor', [
        ('latitud', '-91'),
        ('longitud', '181'),
        ('telefono_contacto', 'llamame'),
        ('horas_limite_cancelacion', -1),
        ('nombre', '<b></b>'),
    ])
    def test_rechaza_datos_invalidos(self, superadmin, dueno, cliente_de, campo, valor):
        respuesta = cliente_de(superadmin).post(URL, _datos_alta(dueno, **{campo: valor}), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_dueno_no_puede_dar_de_alta_contratos(self, dueno, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(dueno), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not Complejo.objects.filter(nombre='Complejo Nuevo').exists()
        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO, usuario=dueno).exists()


class TestCambioDeEstadoDeContrato:
    def _cambiar(self, cliente, complejo, estado):
        return cliente.patch(f'{URL}{complejo.id}/', {'estado_contrato': estado}, format='json')

    def test_suspende_y_audita_la_transicion(self, superadmin, complejo, cliente_de):
        respuesta = self._cambiar(cliente_de(superadmin), complejo, EstadoContrato.SUSPENDIDO)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado_contrato'] == EstadoContrato.SUSPENDIDO
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONTRATO)
        assert log.detalle == 'Activo -> Suspendido.'
        assert log.complejo == complejo

    def test_la_baja_del_contrato_conserva_el_historial(
        self, superadmin, dueno, complejo, crear_cancha, cliente_de,
    ):
        cancha = crear_cancha(complejo)

        self._cambiar(cliente_de(superadmin), complejo, EstadoContrato.BAJA)

        complejo.refresh_from_db()
        assert complejo.estado_contrato == EstadoContrato.BAJA
        assert complejo.estado == EstadoRegistro.ACTIVO
        assert Cancha.objects.get(id=cancha.id).estado == EstadoCancha.ACTIVA
        assert cliente_de(superadmin).get(URL, {'estado_contrato': 0}).json()['count'] == 1
        administrados = cliente_de(dueno).get('/api/complejos/administrados/').json()['results']
        assert [item['id'] for item in administrados] == [complejo.id]

    def test_reactivar_vuelve_a_publicar(self, superadmin, dueno, crear_complejo, cliente, cliente_de):
        suspendido = crear_complejo(dueno, 'Suspendido', estado_contrato=EstadoContrato.SUSPENDIDO)

        self._cambiar(cliente_de(superadmin), suspendido, EstadoContrato.ACTIVO)

        assert cliente.get(f'/api/complejos/{suspendido.id}/').status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('estado', [EstadoUsuario.SUSPENDIDO, EstadoUsuario.BAJA])
    def test_no_activa_si_el_propietario_no_esta_activo(
        self, superadmin, dueno, crear_complejo, cliente_de, estado,
    ):
        pendiente = crear_complejo(dueno, 'Pendiente', estado_contrato=EstadoContrato.PENDIENTE)
        dueno.estado = estado
        dueno.save(update_fields=['estado'])

        respuesta = self._cambiar(cliente_de(superadmin), pendiente, EstadoContrato.ACTIVO)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        pendiente.refresh_from_db()
        assert pendiente.estado_contrato == EstadoContrato.PENDIENTE

    def test_el_mismo_estado_no_genera_auditoria(self, superadmin, complejo, cliente_de):
        respuesta = self._cambiar(cliente_de(superadmin), complejo, EstadoContrato.ACTIVO)

        assert respuesta.status_code == status.HTTP_200_OK
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_CONTRATO).exists()

    def test_solo_modifica_el_estado_del_contrato(self, superadmin, complejo, cliente_de):
        cliente_de(superadmin).patch(
            f'{URL}{complejo.id}/', {'estado_contrato': EstadoContrato.SUSPENDIDO, 'nombre': 'Otro'}, format='json',
        )

        complejo.refresh_from_db()
        assert complejo.nombre == 'Complejo Propio'

    @pytest.mark.parametrize('cuerpo', [{'estado_contrato': 9}, {'estado_contrato': 'activo'}, {}])
    def test_estado_invalido_responde_400(self, superadmin, complejo, cliente_de, cuerpo):
        respuesta = cliente_de(superadmin).patch(f'{URL}{complejo.id}/', cuerpo, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_complejo_inexistente_responde_404(self, superadmin, cliente_de):
        respuesta = cliente_de(superadmin).patch(f'{URL}999999/', {'estado_contrato': 3}, format='json')

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_dueno_no_puede_cambiar_su_contrato(self, dueno, complejo, cliente_de):
        respuesta = self._cambiar(cliente_de(dueno), complejo, EstadoContrato.SUSPENDIDO)

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        complejo.refresh_from_db()
        assert complejo.estado_contrato == EstadoContrato.ACTIVO

    def test_no_se_borra_fisicamente(self, superadmin, complejo, cliente_de):
        assert cliente_de(superadmin).delete(f'{URL}{complejo.id}/').status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Complejo.objects.filter(id=complejo.id).exists()
