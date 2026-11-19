from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken

from core.models import (
    EstadoContrato,
    EstadoUsuario,
    LogAuditoria,
    Rol,
    RolPermiso,
    TipoEventoAuditoria,
    Usuario,
)
from core.repositories import UsuarioRepository
from core.serializers_auth import TokenConRolSerializer
from conftest import PASSWORD_PRUEBA

URL = '/api/usuarios/'

CAMPOS_EXPUESTOS = {
    'id', 'email', 'nombre_completo', 'telefono', 'rol', 'complejo_operado', 'complejo_operado_nombre', 'estado',
    'estado_nombre', 'version_politica_aceptada', 'fecha_aceptacion_politica', 'fecha_creacion',
    'fecha_modificacion',
}


def _patch(cliente, usuario, cuerpo):
    return cliente.patch(f'{URL}{usuario.id}/', cuerpo, format='json')


def _refresh_vigentes(usuario):
    return OutstandingToken.objects.filter(user_id=usuario.id, blacklistedtoken__isnull=True).count()


class TestConsultaDeUsuarios:
    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno'])
    def test_roles_sin_permiso_reciben_403(self, request, jugador, cliente_de, fixture_usuario):
        cliente = cliente_de(request.getfixturevalue(fixture_usuario))

        assert cliente.get(URL).status_code == status.HTTP_403_FORBIDDEN
        assert cliente.get(f'{URL}{jugador.id}/').status_code == status.HTTP_403_FORBIDDEN

    def test_superadmin_lista_paginado_con_campos_declarados(self, superadmin, jugador, dueno, cliente_de):
        respuesta = cliente_de(superadmin).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['count'] == 3
        assert set(respuesta.json()['results'][0]) == CAMPOS_EXPUESTOS
        assert 'password' not in respuesta.content.decode()

    def test_detalle(self, superadmin, operador, complejo, cliente_de):
        datos = cliente_de(superadmin).get(f'{URL}{operador.id}/').json()

        assert datos['rol'] == 'OPERADOR_COMPLEJO'
        assert datos['complejo_operado'] == complejo.id
        assert datos['complejo_operado_nombre'] == 'Complejo Propio'

    def test_detalle_inexistente_responde_404(self, superadmin, cliente_de):
        assert cliente_de(superadmin).get(f'{URL}999999/').status_code == status.HTTP_404_NOT_FOUND

    def test_filtra_por_rol_estado_y_busqueda(self, superadmin, jugador, dueno, crear_usuario, cliente_de):
        suspendido = crear_usuario('suspendido@talibre.test', estado=EstadoUsuario.SUSPENDIDO)
        cliente = cliente_de(superadmin)

        por_rol = cliente.get(URL, {'rol': 'DUENO_COMPLEJO'}).json()['results']
        por_estado = cliente.get(URL, {'estado': EstadoUsuario.SUSPENDIDO}).json()['results']
        por_busqueda = cliente.get(URL, {'search': 'jugador@'}).json()['results']

        assert [usuario['id'] for usuario in por_rol] == [dueno.id]
        assert [usuario['id'] for usuario in por_estado] == [suspendido.id]
        assert [usuario['id'] for usuario in por_busqueda] == [jugador.id]

    def test_la_busqueda_ignora_tildes_y_mayusculas(self, superadmin, crear_usuario, cliente_de):
        tomas = crear_usuario('tomas@talibre.test', nombre_completo='Tomás Valdez')

        for termino in ('tomas', 'TOMÁS valdez', 'Tomas'):
            resultados = cliente_de(superadmin).get(URL, {'search': termino}).json()['results']
            assert [usuario['id'] for usuario in resultados] == [tomas.id], termino

    @pytest.mark.parametrize('parametros', [{'rol': 'ROOT'}, {'estado': 5}])
    def test_filtros_invalidos_responden_400(self, superadmin, cliente_de, parametros):
        assert cliente_de(superadmin).get(URL, parametros).status_code == status.HTTP_400_BAD_REQUEST


class TestEdicionDePerfil:
    def test_edita_nombre_y_telefono_sanitizados(self, superadmin, jugador, cliente_de):
        respuesta = _patch(cliente_de(superadmin), jugador, {
            'nombre_completo': '<img src=x onerror=alert(1)>Jugador Editado', 'telefono': '3777 001222',
        })

        assert respuesta.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Jugador Editado'
        assert jugador.telefono == '3777 001222'

    def test_la_auditoria_no_replica_datos_personales(self, superadmin, jugador, cliente_de):
        _patch(cliente_de(superadmin), jugador, {'nombre_completo': 'Nombre Secreto', 'telefono': '3777 009888'})

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_USUARIO)
        assert log.usuario == superadmin
        assert f'id {jugador.id}' in log.detalle
        assert 'nombre_completo, telefono' in log.detalle
        assert 'Nombre Secreto' not in log.detalle
        assert '009888' not in log.detalle

    def test_no_permite_cambiar_email_ni_password(self, superadmin, jugador, cliente_de):
        respuesta = _patch(cliente_de(superadmin), jugador, {'email': 'otro@talibre.test', 'password': 'Nueva#2026'})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        jugador.refresh_from_db()
        assert jugador.email == 'jugador@talibre.test'
        assert jugador.check_password(PASSWORD_PRUEBA)

    def test_telefono_invalido_responde_400(self, superadmin, jugador, cliente_de):
        assert _patch(cliente_de(superadmin), jugador, {'telefono': 'abc'}).status_code == status.HTTP_400_BAD_REQUEST

    def test_sin_cambios_reales_no_audita(self, superadmin, jugador, cliente_de):
        respuesta = _patch(cliente_de(superadmin), jugador, {'nombre_completo': jugador.nombre_completo})

        assert respuesta.status_code == status.HTTP_200_OK
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_USUARIO).exists()

    def test_dueno_no_puede_editar_usuarios(self, dueno, jugador, cliente_de):
        assert _patch(cliente_de(dueno), jugador, {'nombre_completo': 'X'}).status_code == status.HTTP_403_FORBIDDEN

    def test_usuario_inexistente_responde_404(self, superadmin, cliente_de):
        respuesta = cliente_de(superadmin).patch(f'{URL}999999/', {'nombre_completo': 'X'}, format='json')

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND


class TestSuspensionYBajaAdministrativa:
    def test_suspender_revoca_sesiones_sin_anonimizar(self, superadmin, jugador, cliente_de):
        cliente_jugador = cliente_de(jugador)
        assert _refresh_vigentes(jugador) == 1

        respuesta = _patch(cliente_de(superadmin), jugador, {'estado': EstadoUsuario.SUSPENDIDO})

        assert respuesta.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.estado == EstadoUsuario.SUSPENDIDO
        assert jugador.email == 'jugador@talibre.test'
        assert jugador.nombre_completo == 'Jugador Prueba'
        assert jugador.has_usable_password()
        assert _refresh_vigentes(jugador) == 0
        assert cliente_jugador.get('/api/perfil/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_la_suspension_se_audita(self, superadmin, jugador, cliente_de, log_seguridad):
        _patch(cliente_de(superadmin), jugador, {'estado': EstadoUsuario.SUSPENDIDO})

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_USUARIO)
        assert 'Activo -> Suspendido' in log.detalle
        assert 'Sesiones revocadas' in log.detalle
        assert 'evento=CAMBIO_USUARIO' in log_seguridad.text

    def test_un_usuario_suspendido_no_puede_iniciar_sesion(self, superadmin, jugador, cliente, cliente_de):
        _patch(cliente_de(superadmin), jugador, {'estado': EstadoUsuario.SUSPENDIDO})

        respuesta = cliente.post('/api/token/', {'email': jugador.email, 'password': PASSWORD_PRUEBA}, format='json')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED

    def test_la_baja_administrativa_conserva_los_datos(self, superadmin, jugador, cliente_de):
        jugador.telefono = '3777 000206'
        jugador.save(update_fields=['telefono'])
        cliente_de(jugador)

        respuesta = _patch(cliente_de(superadmin), jugador, {'estado': EstadoUsuario.BAJA})

        assert respuesta.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.estado == EstadoUsuario.BAJA
        assert jugador.email == 'jugador@talibre.test'
        assert jugador.telefono == '3777 000206'
        assert jugador.has_usable_password()
        assert _refresh_vigentes(jugador) == 0
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO)
        assert log.accion == 'Baja administrativa de usuario'
        assert log.usuario == superadmin

    def test_reactiva_una_cuenta_suspendida(self, superadmin, crear_usuario, cliente, cliente_de):
        suspendido = crear_usuario('suspendido@talibre.test', estado=EstadoUsuario.SUSPENDIDO)

        _patch(cliente_de(superadmin), suspendido, {'estado': EstadoUsuario.ACTIVO})

        login = cliente.post('/api/token/', {'email': suspendido.email, 'password': PASSWORD_PRUEBA}, format='json')
        assert login.status_code == status.HTTP_200_OK

    def test_no_modifica_cuentas_anonimizadas_por_su_titular(self, superadmin, jugador, cliente_de):
        assert cliente_de(jugador).delete('/api/perfil/').status_code == status.HTTP_204_NO_CONTENT

        respuesta = _patch(cliente_de(superadmin), jugador, {'estado': EstadoUsuario.ACTIVO})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'anonimizaron' in respuesta.json()['detail']
        jugador.refresh_from_db()
        assert jugador.estado == EstadoUsuario.BAJA

    def test_cambiar_estado_exige_desactivar_usuarios(self, superadmin, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='SUPERADMIN', permiso__codigo='desactivar_usuarios').desactivar()
        cliente = cliente_de(superadmin)

        rechazo = _patch(cliente, jugador, {'estado': EstadoUsuario.SUSPENDIDO, 'nombre_completo': 'Otro'})
        mismo_estado = _patch(cliente, jugador, {'estado': EstadoUsuario.ACTIVO})
        solo_perfil = _patch(cliente, jugador, {'nombre_completo': 'Otro'})

        assert rechazo.status_code == status.HTTP_403_FORBIDDEN
        assert mismo_estado.status_code == status.HTTP_200_OK
        assert solo_perfil.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.estado == EstadoUsuario.ACTIVO

    def test_estado_invalido_responde_400(self, superadmin, jugador, cliente_de):
        assert _patch(cliente_de(superadmin), jugador, {'estado': 9}).status_code == status.HTTP_400_BAD_REQUEST

    def test_cuerpo_vacio_responde_400(self, superadmin, jugador, cliente_de):
        assert _patch(cliente_de(superadmin), jugador, {}).status_code == status.HTTP_400_BAD_REQUEST


class TestResguardoDelUltimoSuperadmin:
    @pytest.mark.parametrize('cuerpo', [
        {'estado': EstadoUsuario.SUSPENDIDO},
        {'estado': EstadoUsuario.BAJA},
        {'rol': 'JUGADOR'},
        {'rol': 'DUENO_COMPLEJO', 'estado': EstadoUsuario.ACTIVO},
    ])
    def test_no_se_puede_desactivar_ni_degradar_al_unico_superadmin(self, superadmin, cliente_de, cuerpo):
        respuesta = _patch(cliente_de(superadmin), superadmin, cuerpo)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'única cuenta de superadministrador activa' in respuesta.json()['detail']
        superadmin.refresh_from_db()
        assert superadmin.estado == EstadoUsuario.ACTIVO
        assert superadmin.rol.nombre == 'SUPERADMIN'
        assert _refresh_vigentes(superadmin) == 1

    def test_un_superadmin_suspendido_no_cuenta_como_reemplazo(self, superadmin, crear_usuario, cliente_de):
        crear_usuario('suspendido@talibre.test', 'SUPERADMIN', estado=EstadoUsuario.SUSPENDIDO)

        respuesta = _patch(cliente_de(superadmin), superadmin, {'estado': EstadoUsuario.SUSPENDIDO})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_con_otro_superadmin_activo_procede(self, superadmin, crear_usuario, cliente_de):
        otro = crear_usuario('otro.superadmin@talibre.test', 'SUPERADMIN')

        primero = _patch(cliente_de(superadmin), otro, {'rol': 'JUGADOR'})
        segundo = _patch(cliente_de(superadmin), superadmin, {'estado': EstadoUsuario.SUSPENDIDO})

        assert primero.status_code == status.HTTP_200_OK
        assert segundo.status_code == status.HTTP_400_BAD_REQUEST

    def test_editar_datos_del_unico_superadmin_esta_permitido(self, superadmin, cliente_de):
        respuesta = _patch(cliente_de(superadmin), superadmin, {'nombre_completo': 'Plataforma', 'estado': 1})

        assert respuesta.status_code == status.HTTP_200_OK

    def test_la_validacion_bloquea_las_filas_de_superadmins(self, superadmin, crear_usuario, cliente_de):
        otro = crear_usuario('otro.superadmin@talibre.test', 'SUPERADMIN')
        original = UsuarioRepository.bloquear_activos_con_rol

        with mock.patch.object(
            UsuarioRepository, 'bloquear_activos_con_rol', side_effect=original,
        ) as bloqueo:
            _patch(cliente_de(superadmin), otro, {'estado': EstadoUsuario.SUSPENDIDO})

        bloqueo.assert_called_with('SUPERADMIN')

    def test_editar_solo_el_perfil_no_bloquea_superadmins(self, superadmin, jugador, cliente_de):
        with mock.patch.object(UsuarioRepository, 'bloquear_activos_con_rol') as bloqueo:
            _patch(cliente_de(superadmin), jugador, {'nombre_completo': 'Otro Nombre'})

        bloqueo.assert_not_called()


class TestCambioDeRol:
    def test_promueve_a_operador_con_complejo(self, superadmin, jugador, complejo, cliente_de):
        respuesta = _patch(cliente_de(superadmin), jugador, {'rol': 'OPERADOR_COMPLEJO', 'complejo_operado': complejo.id})

        assert respuesta.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.rol.nombre == 'OPERADOR_COMPLEJO'
        assert jugador.complejo_operado == complejo
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_USUARIO)
        assert 'Rol: JUGADOR -> OPERADOR_COMPLEJO.' in log.detalle

    def test_el_cambio_de_rol_se_refleja_en_el_refresh(self, superadmin, jugador, cliente_de):
        refresh = TokenConRolSerializer.get_token(jugador)

        _patch(cliente_de(superadmin), jugador, {'rol': 'DUENO_COMPLEJO'})

        cliente = APIClient()
        cliente.cookies['refresh'] = str(refresh)
        respuesta = cliente.post('/api/token/refresh/')
        assert respuesta.status_code == status.HTTP_200_OK
        assert AccessToken(respuesta.json()['access'])['rol'] == 'DUENO_COMPLEJO'

    def test_quitar_el_rol_de_operador_lo_desvincula(self, superadmin, operador, cliente_de):
        _patch(cliente_de(superadmin), operador, {'rol': 'JUGADOR'})

        operador.refresh_from_db()
        assert operador.complejo_operado is None

    def test_solo_un_operador_puede_tener_complejo(self, superadmin, jugador, complejo, cliente_de):
        respuesta = _patch(cliente_de(superadmin), jugador, {'complejo_operado': complejo.id})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'complejo_operado' in respuesta.json()['detail']

    def test_complejo_dado_de_baja_no_es_asignable(self, superadmin, operador, complejo_ajeno, cliente_de):
        complejo_ajeno.desactivar()

        respuesta = _patch(cliente_de(superadmin), operador, {'complejo_operado': complejo_ajeno.id})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_dueno_con_contratos_vigentes_no_cambia_de_rol(self, superadmin, dueno, complejo, cliente_de):
        respuesta = _patch(cliente_de(superadmin), dueno, {'rol': 'JUGADOR'})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'rol' in respuesta.json()['detail']

    def test_dueno_con_contratos_dados_de_baja_puede_cambiar_de_rol(self, superadmin, dueno, complejo, cliente_de):
        complejo.estado_contrato = EstadoContrato.BAJA
        complejo.save(update_fields=['estado_contrato'])

        assert _patch(cliente_de(superadmin), dueno, {'rol': 'JUGADOR'}).status_code == status.HTTP_200_OK

    def test_rol_inexistente_o_dado_de_baja_responde_400(self, superadmin, jugador, cliente_de):
        Rol.objects.get(nombre='OPERADOR_COMPLEJO').desactivar()
        cliente = cliente_de(superadmin)

        assert _patch(cliente, jugador, {'rol': 'ROOT'}).status_code == status.HTTP_400_BAD_REQUEST
        assert _patch(cliente, jugador, {'rol': 'OPERADOR_COMPLEJO'}).status_code == status.HTTP_400_BAD_REQUEST
        assert Usuario.objects.get(id=jugador.id).rol.nombre == 'JUGADOR'
