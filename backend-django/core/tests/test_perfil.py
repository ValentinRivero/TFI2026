import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework import status

from conftest import PASSWORD_PRUEBA
from core.models import EstadoContrato, EstadoRegistro, EstadoUsuario, LogAuditoria, RolPermiso, TipoEventoAuditoria

URL = '/api/perfil/'


class TestConsulta:
    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno', 'superadmin'])
    def test_todos_los_roles_ven_su_perfil(self, request, cliente_de, fixture_usuario):
        usuario = request.getfixturevalue(fixture_usuario)

        respuesta = cliente_de(usuario).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['email'] == usuario.email
        assert respuesta.json()['rol'] == usuario.rol.nombre

    def test_no_expone_la_contrasena(self, jugador, cliente_de):
        cuerpo = cliente_de(jugador).get(URL).json()

        assert 'password' not in cuerpo
        assert set(cuerpo) == {
            'id', 'email', 'nombre_completo', 'telefono', 'rol',
            'complejo_operado', 'estado', 'estado_nombre', 'version_politica_aceptada',
            'fecha_aceptacion_politica', 'debe_aceptar_politica', 'fecha_creacion',
        }

    def test_operador_ve_su_complejo(self, operador, complejo, cliente_de):
        assert cliente_de(operador).get(URL).json()['complejo_operado'] == complejo.id

    def test_sin_permiso_ver_perfil_propio_responde_403(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='ver_perfil_propio').desactivar()

        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN


class TestEdicion:
    def test_edita_nombre_y_telefono(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(
            URL, {'nombre_completo': 'Jugador Editado', 'telefono': '+54 3777 123456'}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Jugador Editado'
        assert jugador.telefono == '+54 3777 123456'

    def test_edicion_parcial_conserva_lo_demas(self, jugador, cliente_de):
        cliente_de(jugador).patch(URL, {'telefono': '3777 999999'}, format='json')

        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Jugador Prueba'
        assert jugador.telefono == '3777 999999'

    def test_no_permite_cambiar_email_rol_ni_estado(self, jugador, cliente_de):
        cliente_de(jugador).patch(
            URL,
            {'nombre_completo': 'Otro Nombre', 'email': 'nuevo@talibre.test', 'rol': 1, 'estado': 2},
            format='json',
        )

        jugador.refresh_from_db()
        assert jugador.email == 'jugador@talibre.test'
        assert jugador.rol.nombre == 'JUGADOR'
        assert jugador.estado == EstadoRegistro.ACTIVO

    def test_sanitiza_el_nombre(self, jugador, cliente_de):
        cliente_de(jugador).patch(URL, {'nombre_completo': '<img src=x onerror=alert(1)>Ana & Cía'}, format='json')

        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Ana & Cía'

    @pytest.mark.parametrize('datos, campo', [
        ({'nombre_completo': '<b></b>'}, 'nombre_completo'),
        ({'telefono': 'sin número'}, 'telefono'),
        ({'nombre_completo': 'x' * 121}, 'nombre_completo'),
    ])
    def test_rechaza_datos_invalidos(self, jugador, cliente_de, datos, campo):
        respuesta = cliente_de(jugador).patch(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_body_vacio_responde_400(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(URL, {}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['error'] is True

    def test_sin_permiso_editar_responde_403_y_audita(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='editar_perfil_propio').desactivar()
        cliente = cliente_de(jugador)

        respuesta = cliente.patch(URL, {'telefono': '3777 000000'}, format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert respuesta.json() == {'error': True, 'detail': 'No tenés permiso para realizar esta acción.'}
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO)
        assert log.usuario == jugador
        assert log.accion == 'PATCH /api/perfil/'
        assert cliente.get(URL).status_code == status.HTTP_200_OK


class TestBajaLogica:
    def test_baja_logica_con_estado_cero(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).delete(URL)

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        jugador.refresh_from_db()
        assert jugador.estado == EstadoRegistro.BAJA
        assert type(jugador).objects.filter(pk=jugador.pk).exists()

    def test_audita_la_baja(self, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO)
        assert log.usuario == jugador

    def test_el_access_deja_de_servir(self, jugador, cliente_de):
        cliente = cliente_de(jugador)
        cliente.delete(URL)

        respuesta = cliente.get(URL)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['detail'] == 'La cuenta no está activa.'

    def test_revoca_las_sesiones_abiertas_y_borra_la_cookie(self, cliente, jugador, cliente_de):
        cliente.post('/api/token/', {'email': jugador.email, 'password': PASSWORD_PRUEBA}, format='json')
        refresh = cliente.cookies['refresh'].value

        respuesta = cliente_de(jugador).delete(URL)

        assert respuesta.cookies['refresh'].value == ''
        cliente.cookies['refresh'] = refresh
        assert cliente.post('/api/token/refresh/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_puede_volver_a_iniciar_sesion(self, cliente, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        respuesta = cliente.post('/api/token/', {'email': jugador.email, 'password': PASSWORD_PRUEBA}, format='json')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED

    def test_el_unico_superadmin_activo_no_puede_darse_de_baja(self, superadmin, cliente_de):
        respuesta = cliente_de(superadmin).delete(URL)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'única cuenta de superadministrador activa' in respuesta.json()['detail']
        superadmin.refresh_from_db()
        assert superadmin.estado == EstadoRegistro.ACTIVO
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO).exists()

    def test_un_superadmin_suspendido_no_cuenta_como_reemplazo(self, superadmin, crear_usuario, cliente_de):
        suspendido = crear_usuario('suspendido@talibre.test', 'SUPERADMIN')
        suspendido.estado = EstadoUsuario.SUSPENDIDO
        suspendido.save(update_fields=['estado'])

        assert cliente_de(superadmin).delete(URL).status_code == status.HTTP_400_BAD_REQUEST

    def test_con_otro_superadmin_activo_la_baja_procede(self, superadmin, crear_usuario, cliente_de):
        otro = crear_usuario('otro.superadmin@talibre.test', 'SUPERADMIN')

        assert cliente_de(superadmin).delete(URL).status_code == status.HTTP_204_NO_CONTENT
        superadmin.refresh_from_db()
        assert superadmin.estado == EstadoRegistro.BAJA
        assert cliente_de(otro).delete(URL).status_code == status.HTTP_400_BAD_REQUEST

    def test_la_auditoria_de_la_baja_no_guarda_el_email(self, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        assert jugador.email not in LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO).detalle

    def test_sin_permiso_desactivar_responde_403(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='desactivar_perfil_propio').desactivar()

        assert cliente_de(jugador).delete(URL).status_code == status.HTTP_403_FORBIDDEN
        jugador.refresh_from_db()
        assert jugador.estado == EstadoRegistro.ACTIVO


class TestAceptacionDePolitica:
    def test_una_cuenta_sin_constancia_debe_aceptar_la_politica(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).json()['debe_aceptar_politica'] is True

    def test_aceptar_la_version_vigente_deja_constancia_y_auditoria(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(URL, {'acepta_politica_privacidad': True}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['debe_aceptar_politica'] is False
        jugador.refresh_from_db()
        assert jugador.version_politica_aceptada == settings.POLITICA_PRIVACIDAD_VERSION
        assert jugador.fecha_aceptacion_politica is not None
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ACEPTACION_POLITICA)
        assert log.usuario == jugador
        assert log.ip_origen == '127.0.0.1'

    def test_no_admite_aceptacion_falsa(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(URL, {'acepta_politica_privacidad': False}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'acepta_politica_privacidad' in respuesta.json()['detail']

    def test_editar_datos_no_registra_aceptacion(self, jugador, cliente_de):
        cliente_de(jugador).patch(URL, {'telefono': '3777 111111'}, format='json')

        jugador.refresh_from_db()
        assert jugador.fecha_aceptacion_politica is None
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACEPTACION_POLITICA).exists()

    def test_una_version_nueva_pide_aceptarla_otra_vez(self, jugador, cliente_de):
        cliente = cliente_de(jugador)
        cliente.patch(URL, {'acepta_politica_privacidad': True}, format='json')

        with override_settings(POLITICA_PRIVACIDAD_VERSION='2.0'):
            assert cliente.get(URL).json()['debe_aceptar_politica'] is True

    def test_el_admin_no_permite_editar_la_constancia(self):
        from django.contrib import admin

        from core.models import Usuario

        campos = admin.site._registry[Usuario].readonly_fields
        assert {'version_politica_aceptada', 'fecha_aceptacion_politica'}.issubset(campos)


class TestSupresionDeDatos:
    def test_la_baja_anonimiza_los_datos_personales(self, jugador, cliente_de):
        jugador.telefono = '3777 501122'
        jugador.save(update_fields=['telefono'])

        cliente_de(jugador).delete(URL)

        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Usuario dado de baja'
        assert jugador.email == f'baja-{jugador.pk}@talibre.invalid'
        assert jugador.telefono == ''
        assert not jugador.has_usable_password()
        assert jugador.estado == EstadoRegistro.BAJA

    def test_el_email_original_queda_libre_para_registrarse_de_nuevo(self, cliente, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        respuesta = cliente.post('/api/registro/', {
            'nombre_completo': 'Jugador Vuelve',
            'email': 'jugador@talibre.test',
            'password': 'Pelota&Arco#2026',
            'acepta_politica_privacidad': True,
        }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_el_operador_se_desvincula_de_su_complejo(self, operador, cliente_de):
        cliente_de(operador).delete(URL)

        operador.refresh_from_db()
        assert operador.complejo_operado is None

    def test_la_auditoria_conserva_la_referencia_sin_datos_personales(self, jugador, cliente_de):
        email = jugador.email
        cliente_de(jugador).delete(URL)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO)
        assert log.usuario_id == jugador.pk
        assert email not in log.detalle
        assert 'anonimizados' in log.detalle

    def test_dueno_con_contrato_vigente_no_puede_darse_de_baja(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).delete(URL)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'contrato vigente' in respuesta.json()['detail']
        dueno.refresh_from_db()
        assert dueno.estado == EstadoRegistro.ACTIVO
        assert dueno.email == 'dueno@talibre.test'

    @pytest.mark.parametrize('dar_de_baja', ['contrato', 'complejo'])
    def test_dueno_sin_contratos_vigentes_puede_darse_de_baja(self, dueno, complejo, cliente_de, dar_de_baja):
        if dar_de_baja == 'contrato':
            complejo.estado_contrato = EstadoContrato.BAJA
            complejo.save(update_fields=['estado_contrato'])
        else:
            complejo.desactivar()

        assert cliente_de(dueno).delete(URL).status_code == status.HTTP_204_NO_CONTENT

    def test_si_la_baja_se_rechaza_no_se_anonimiza_nada(self, superadmin, cliente_de):
        cliente_de(superadmin).delete(URL)

        superadmin.refresh_from_db()
        assert superadmin.email == 'superadmin@talibre.test'
        assert superadmin.has_usable_password()
