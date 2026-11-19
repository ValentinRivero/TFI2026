import pytest
from rest_framework import status

from core.models import (
    ComplejoServicio,
    EstadoContrato,
    EstadoRegistro,
    EstadoUsuario,
    LogAuditoria,
    RolPermiso,
    Servicio,
    TipoEventoAuditoria,
)

URL = '/api/complejos/'
URL_ADMINISTRADOS = f'{URL}administrados/'


def _servicio(nombre):
    return Servicio.objects.get(nombre=nombre)


def _activos(complejo):
    return set(
        ComplejoServicio.objects.filter(complejo=complejo, estado=EstadoRegistro.ACTIVO)
        .values_list('servicio__nombre', flat=True)
    )


class TestComplejosAdministrados:
    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL_ADMINISTRADOS).status_code == status.HTTP_401_UNAUTHORIZED

    def test_jugador_recibe_403(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL_ADMINISTRADOS).status_code == status.HTTP_403_FORBIDDEN

    def test_dueno_ve_sus_complejos_en_cualquier_estado_de_contrato(
        self, dueno, complejo, complejo_ajeno, crear_complejo, cliente_de,
    ):
        suspendido = crear_complejo(dueno, 'Mi Suspendido', estado_contrato=EstadoContrato.SUSPENDIDO)

        respuesta = cliente_de(dueno).get(URL_ADMINISTRADOS)

        assert respuesta.status_code == status.HTTP_200_OK
        assert {item['id'] for item in respuesta.json()['results']} == {complejo.id, suspendido.id}
        assert set(respuesta.json()) == {'count', 'next', 'previous', 'results'}

    def test_operador_ve_solo_su_complejo_asignado(self, operador, complejo, complejo_ajeno, cliente_de):
        resultados = cliente_de(operador).get(URL_ADMINISTRADOS).json()['results']

        assert [item['id'] for item in resultados] == [complejo.id]

    def test_operador_sin_complejo_no_ve_ninguno(self, crear_usuario, complejo, cliente_de):
        suelto = crear_usuario('suelto@talibre.test', 'OPERADOR_COMPLEJO')

        assert cliente_de(suelto).get(URL_ADMINISTRADOS).json()['count'] == 0

    def test_superadmin_ve_todos_los_vigentes(self, superadmin, complejo, complejo_ajeno, crear_complejo, dueno, cliente_de):
        de_baja = crear_complejo(dueno, 'Dado de baja')
        de_baja.desactivar()

        resultados = cliente_de(superadmin).get(URL_ADMINISTRADOS).json()['results']

        assert {item['id'] for item in resultados} == {complejo.id, complejo_ajeno.id}

    def test_incluye_estado_de_contrato_y_servicios(self, dueno, complejo, ofrecer_servicios, cliente_de):
        ofrecer_servicios(complejo, 'Buffet')

        item = cliente_de(dueno).get(URL_ADMINISTRADOS).json()['results'][0]

        assert item['estado_contrato_nombre'] == 'Activo'
        assert [servicio['nombre'] for servicio in item['servicios']] == ['Buffet']


class TestConfiguracionDelComplejo:
    def _patch(self, cliente, complejo, cuerpo):
        return cliente.patch(f'{URL}{complejo.id}/', cuerpo, format='json')

    def test_dueno_actualiza_su_complejo(self, dueno, complejo, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo, {
            'nombre': 'El Yacaré',
            'direccion': 'Av. del Ombú 1250, Goya',
            'latitud': '-29.145000',
            'longitud': '-59.272500',
            'telefono_contacto': '3777 000101',
            'horas_limite_cancelacion': 12,
            'info_sena': 'Seña del 30% por transferencia.',
        })

        assert respuesta.status_code == status.HTTP_200_OK
        complejo.refresh_from_db()
        assert complejo.nombre == 'El Yacaré'
        assert str(complejo.latitud) == '-29.145000'
        assert complejo.horas_limite_cancelacion == 12
        assert respuesta.json()['info_sena'] == 'Seña del 30% por transferencia.'

    def test_sanitiza_contra_xss(self, dueno, complejo, cliente_de):
        self._patch(cliente_de(dueno), complejo, {
            'nombre': '<script>alert(1)</script>Complejo Seguro',
            'info_sena': '&lt;img src=x onerror=alert(1)&gt;Alias PAGO.GOYA & Cía',
        })

        complejo.refresh_from_db()
        assert complejo.nombre == 'Complejo Seguro'
        assert complejo.info_sena == 'Alias PAGO.GOYA & Cía'

    def test_audita_solo_los_nombres_de_los_campos(self, dueno, complejo, cliente_de):
        self._patch(cliente_de(dueno), complejo, {'info_sena': 'Alias SECRETO.123', 'horas_limite_cancelacion': 6})

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION)
        assert log.detalle == 'Campos modificados: horas_limite_cancelacion, info_sena.'
        assert log.complejo == complejo
        assert log.usuario == dueno

    def test_sin_cambios_reales_no_audita(self, dueno, complejo, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo, {'nombre': complejo.nombre})

        assert respuesta.status_code == status.HTTP_200_OK
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION).exists()

    def test_no_permite_tocar_contrato_ni_propietario(self, dueno, otro_dueno, complejo, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo, {
            'nombre': 'Renombrado', 'estado_contrato': EstadoContrato.BAJA, 'propietario': otro_dueno.id,
        })

        assert respuesta.status_code == status.HTTP_200_OK
        complejo.refresh_from_db()
        assert complejo.estado_contrato == EstadoContrato.ACTIVO
        assert complejo.propietario == dueno

    def test_superadmin_configura_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        respuesta = self._patch(cliente_de(superadmin), complejo_ajeno, {'horas_limite_cancelacion': 2})

        assert respuesta.status_code == status.HTTP_200_OK

    def test_el_superadmin_conserva_el_acceso_aunque_le_quiten_el_permiso_heredable(
        self, superadmin, complejo_ajeno, cliente_de,
    ):
        RolPermiso.objects.get(rol__nombre='SUPERADMIN', permiso__codigo='configurar_complejo').desactivar()

        respuesta = self._patch(cliente_de(superadmin), complejo_ajeno, {'horas_limite_cancelacion': 2})

        assert respuesta.status_code == status.HTTP_200_OK

    def test_operador_no_configura_el_complejo(self, operador, complejo, cliente_de):
        respuesta = self._patch(cliente_de(operador), complejo, {'info_sena': 'Cambiada'})

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN

    def test_complejo_ajeno_responde_404(self, dueno, complejo_ajeno, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo_ajeno, {'nombre': 'Robado'})

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        complejo_ajeno.refresh_from_db()
        assert complejo_ajeno.nombre == 'Complejo Ajeno'

    def test_complejo_dado_de_baja_responde_404(self, dueno, complejo, cliente_de):
        complejo.desactivar()

        assert self._patch(cliente_de(dueno), complejo, {'nombre': 'X'}).status_code == status.HTTP_404_NOT_FOUND

    def test_dueno_configura_su_complejo_aunque_el_contrato_este_suspendido(self, dueno, complejo, cliente_de):
        complejo.estado_contrato = EstadoContrato.SUSPENDIDO
        complejo.save(update_fields=['estado_contrato'])

        assert self._patch(cliente_de(dueno), complejo, {'nombre': 'X'}).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('campo, valor', [
        ('latitud', '95'),
        ('longitud', '-200'),
        ('telefono_contacto', 'sin numero'),
        ('horas_limite_cancelacion', -3),
        ('info_sena', 'x' * 201),
        ('nombre', '<i></i>'),
    ])
    def test_datos_invalidos_responden_400(self, dueno, complejo, cliente_de, campo, valor):
        respuesta = self._patch(cliente_de(dueno), complejo, {campo: valor})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_cuerpo_vacio_responde_400(self, dueno, complejo, cliente_de):
        assert self._patch(cliente_de(dueno), complejo, {}).status_code == status.HTTP_400_BAD_REQUEST

    def test_put_y_delete_del_complejo_no_estan_permitidos(self, superadmin, complejo, cliente_de):
        cliente = cliente_de(superadmin)

        assert cliente.put(f'{URL}{complejo.id}/', {}, format='json').status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert cliente.delete(f'{URL}{complejo.id}/').status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestServiciosDelComplejo:
    def _put(self, cliente, complejo, nombres):
        return cliente.put(
            f'{URL}{complejo.id}/servicios/', {'servicios': [_servicio(nombre).id for nombre in nombres]},
            format='json',
        )

    def test_sincroniza_con_baja_y_alta_logica(self, dueno, complejo, ofrecer_servicios, cliente_de):
        ofrecer_servicios(complejo, 'Buffet', 'Duchas')

        respuesta = self._put(cliente_de(dueno), complejo, ['Duchas', 'Wi-Fi'])

        assert respuesta.status_code == status.HTTP_200_OK
        assert [servicio['nombre'] for servicio in respuesta.json()['servicios']] == ['Duchas', 'Wi-Fi']
        assert _activos(complejo) == {'Duchas', 'Wi-Fi'}
        assert ComplejoServicio.objects.get(complejo=complejo, servicio__nombre='Buffet').estado == EstadoRegistro.BAJA

    def test_reactiva_la_misma_fila_sin_duplicar(self, dueno, complejo, ofrecer_servicios, cliente_de):
        (asignacion,) = ofrecer_servicios(complejo, 'Buffet')
        cliente = cliente_de(dueno)

        self._put(cliente, complejo, [])
        self._put(cliente, complejo, ['Buffet'])

        assert ComplejoServicio.objects.filter(complejo=complejo).count() == 1
        asignacion.refresh_from_db()
        assert asignacion.estado == EstadoRegistro.ACTIVO

    def test_lista_vacia_quita_todos(self, dueno, complejo, ofrecer_servicios, cliente_de):
        ofrecer_servicios(complejo, 'Buffet', 'Duchas')

        respuesta = self._put(cliente_de(dueno), complejo, [])

        assert respuesta.json() == {'servicios': []}
        assert _activos(complejo) == set()

    def test_los_ids_repetidos_no_duplican(self, dueno, complejo, cliente_de):
        servicio = _servicio('Buffet').id

        cliente_de(dueno).put(f'{URL}{complejo.id}/servicios/', {'servicios': [servicio, servicio]}, format='json')

        assert ComplejoServicio.objects.filter(complejo=complejo).count() == 1

    def test_audita_altas_y_bajas(self, dueno, complejo, ofrecer_servicios, cliente_de):
        ofrecer_servicios(complejo, 'Buffet')

        self._put(cliente_de(dueno), complejo, ['Duchas'])

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION)
        assert log.accion == 'Cambio de servicios del complejo'
        assert str(_servicio('Duchas').id) in log.detalle
        assert str(_servicio('Buffet').id) in log.detalle

    def test_sin_cambios_no_audita(self, dueno, complejo, ofrecer_servicios, cliente_de):
        ofrecer_servicios(complejo, 'Buffet')

        self._put(cliente_de(dueno), complejo, ['Buffet'])

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION).exists()

    def test_el_catalogo_refleja_los_servicios(self, dueno, complejo, cliente, cliente_de):
        self._put(cliente_de(dueno), complejo, ['Wi-Fi'])

        detalle = cliente.get(f'{URL}{complejo.id}/').json()

        assert [servicio['nombre'] for servicio in detalle['servicios']] == ['Wi-Fi']

    @pytest.mark.parametrize('cuerpo', [{}, {'servicios': [999999]}, {'servicios': 'Wi-Fi'}])
    def test_datos_invalidos_responden_400(self, dueno, complejo, cliente_de, cuerpo):
        respuesta = cliente_de(dueno).put(f'{URL}{complejo.id}/servicios/', cuerpo, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_un_servicio_dado_de_baja_no_es_asignable(self, dueno, complejo, cliente_de):
        _servicio('Wi-Fi').desactivar()

        assert self._put(cliente_de(dueno), complejo, ['Wi-Fi']).status_code == status.HTTP_400_BAD_REQUEST

    def test_operador_recibe_403(self, operador, complejo, cliente_de):
        assert self._put(cliente_de(operador), complejo, ['Wi-Fi']).status_code == status.HTTP_403_FORBIDDEN

    def test_complejo_ajeno_responde_404(self, dueno, complejo_ajeno, cliente_de):
        assert self._put(cliente_de(dueno), complejo_ajeno, ['Wi-Fi']).status_code == status.HTTP_404_NOT_FOUND
        assert _activos(complejo_ajeno) == set()

    def test_superadmin_sincroniza_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        assert self._put(cliente_de(superadmin), complejo_ajeno, ['Wi-Fi']).status_code == status.HTTP_200_OK


class TestOperadoresDelComplejo:
    @pytest.fixture
    def operador_libre(self, crear_usuario):
        return crear_usuario('libre@talibre.test', 'OPERADOR_COMPLEJO', nombre_completo='Operador Libre')

    def _url(self, complejo, usuario=None):
        return f'{URL}{complejo.id}/operadores/' + (f'{usuario.id}/' if usuario else '')

    def test_dueno_lista_sus_operadores_paginados(self, dueno, operador, complejo, cliente_de):
        respuesta = cliente_de(dueno).get(self._url(complejo))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['count'] == 1
        assert set(respuesta.json()['results'][0]) == {
            'id', 'nombre_completo', 'email', 'telefono', 'estado', 'estado_nombre',
        }

    def test_operador_no_ve_la_nomina(self, operador, complejo, cliente_de):
        assert cliente_de(operador).get(self._url(complejo)).status_code == status.HTTP_403_FORBIDDEN

    def test_los_operadores_dados_de_baja_no_se_listan(self, dueno, operador, complejo, cliente_de):
        operador.estado = EstadoUsuario.BAJA
        operador.save(update_fields=['estado'])

        assert cliente_de(dueno).get(self._url(complejo)).json()['count'] == 0

    def test_vincula_un_operador_libre(self, dueno, complejo, operador_libre, cliente_de):
        respuesta = cliente_de(dueno).post(self._url(complejo), {'email': operador_libre.email}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        operador_libre.refresh_from_db()
        assert operador_libre.complejo_operado == complejo
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION)
        assert log.detalle == f'Operador: id {operador_libre.id}.'
        assert operador_libre.email not in log.detalle

    def test_el_operador_vinculado_accede_al_panel(self, dueno, complejo, operador_libre, cliente_de):
        cliente_de(dueno).post(self._url(complejo), {'email': operador_libre.email}, format='json')

        resultados = cliente_de(operador_libre).get(URL_ADMINISTRADOS).json()['results']

        assert [item['id'] for item in resultados] == [complejo.id]

    def test_las_cuentas_no_disponibles_dan_el_mismo_error(
        self, dueno, jugador, complejo, complejo_ajeno, crear_usuario, cliente_de,
    ):
        ocupado = crear_usuario('ocupado@talibre.test', 'OPERADOR_COMPLEJO', complejo_operado=complejo_ajeno)
        suspendido = crear_usuario('susp@talibre.test', 'OPERADOR_COMPLEJO', estado=EstadoUsuario.SUSPENDIDO)
        cliente = cliente_de(dueno)

        respuestas = [
            cliente.post(self._url(complejo), {'email': email}, format='json')
            for email in (jugador.email, ocupado.email, suspendido.email, 'nadie@talibre.test')
        ]

        assert {respuesta.status_code for respuesta in respuestas} == {status.HTTP_400_BAD_REQUEST}
        assert len({str(respuesta.json()) for respuesta in respuestas}) == 1
        ocupado.refresh_from_db()
        assert ocupado.complejo_operado == complejo_ajeno

    def test_el_email_no_distingue_mayusculas(self, dueno, complejo, operador_libre, cliente_de):
        respuesta = cliente_de(dueno).post(self._url(complejo), {'email': '  LIBRE@TaLibre.test '}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_ya_no_acepta_vincular_por_id(self, dueno, complejo, operador_libre, cliente_de):
        respuesta = cliente_de(dueno).post(self._url(complejo), {'usuario': operador_libre.id}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in respuesta.json()['detail']
        operador_libre.refresh_from_db()
        assert operador_libre.complejo_operado is None

    def test_un_operador_ya_vinculado_se_rechaza(self, dueno, operador, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(self._url(complejo), {'email': operador.email}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_cuerpo_invalido_responde_400(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(self._url(complejo), {}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_operador_no_vincula_colegas(self, operador, complejo, operador_libre, cliente_de):
        respuesta = cliente_de(operador).post(self._url(complejo), {'email': operador_libre.email}, format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN

    def test_desvincula_un_operador(self, dueno, operador, complejo, cliente_de):
        respuesta = cliente_de(dueno).delete(self._url(complejo, operador))

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        operador.refresh_from_db()
        assert operador.complejo_operado is None
        assert operador.estado == EstadoUsuario.ACTIVO
        assert cliente_de(operador).get(URL_ADMINISTRADOS).json()['count'] == 0

    def test_desvincular_un_operador_de_otro_complejo_responde_404(
        self, dueno, complejo, complejo_ajeno, crear_usuario, cliente_de,
    ):
        ajeno = crear_usuario('ajeno.op@talibre.test', 'OPERADOR_COMPLEJO', complejo_operado=complejo_ajeno)

        respuesta = cliente_de(dueno).delete(self._url(complejo, ajeno))

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        ajeno.refresh_from_db()
        assert ajeno.complejo_operado == complejo_ajeno

    @pytest.mark.parametrize('metodo', ['get', 'post'])
    def test_complejo_ajeno_responde_404(self, dueno, complejo_ajeno, operador_libre, cliente_de, metodo):
        cliente = cliente_de(dueno)
        respuesta = getattr(cliente, metodo)(self._url(complejo_ajeno), {'email': operador_libre.email}, format='json')

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_superadmin_gestiona_operadores_de_cualquier_complejo(
        self, superadmin, complejo_ajeno, operador_libre, cliente_de,
    ):
        cliente = cliente_de(superadmin)

        alta = cliente.post(self._url(complejo_ajeno), {'email': operador_libre.email}, format='json')
        baja = cliente.delete(self._url(complejo_ajeno, operador_libre))

        assert alta.status_code == status.HTTP_201_CREATED
        assert baja.status_code == status.HTTP_204_NO_CONTENT
