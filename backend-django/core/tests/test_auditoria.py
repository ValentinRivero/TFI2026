from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.db import DatabaseError
from django.utils import timezone
from rest_framework import status

from config import settings as settings_base
from core.models import LogAuditoria, TipoEventoAuditoria
from core.services import AuditoriaService

URL = '/api/auditoria/'


class TestRegistroDual:
    def test_escribe_en_la_tabla_y_en_el_logger_seguridad(self, jugador, complejo, log_seguridad):
        log = AuditoriaService.registrar(
            TipoEventoAuditoria.ALTA_EXCEPCION, 'Alta de excepción horaria',
            detalle='Feriado', usuario=jugador, complejo=complejo, ip_origen='10.1.2.3',
        )

        guardado = LogAuditoria.objects.get(pk=log.pk)
        assert guardado.tipo_evento == TipoEventoAuditoria.ALTA_EXCEPCION
        assert guardado.usuario == jugador
        assert guardado.complejo == complejo
        assert guardado.ip_origen == '10.1.2.3'
        registro = log_seguridad.records[-1]
        assert registro.name == 'seguridad'
        assert 'evento=ALTA_EXCEPCION' in registro.getMessage()
        assert f'usuario={jugador.id}' in registro.getMessage()
        assert 'ip=10.1.2.3' in registro.getMessage()

    def test_eventos_de_riesgo_se_loguean_como_warning(self, rbac, log_seguridad):
        AuditoriaService.registrar(TipoEventoAuditoria.LOGIN_FALLIDO, 'Inicio de sesión fallido')

        assert log_seguridad.records[-1].levelname == 'WARNING'

    def test_la_configuracion_base_envia_seguridad_a_security_log(self):
        config = settings_base.LOGGING

        assert 'archivo_seguridad' in config['loggers']['seguridad']['handlers']
        assert str(config['handlers']['archivo_seguridad']['filename']).endswith('security.log')

    def test_una_falla_de_base_no_interrumpe_el_flujo(self, rbac, log_seguridad):
        with mock.patch('core.services.AuditoriaRepository.crear', side_effect=DatabaseError('caída')):
            resultado = AuditoriaService.registrar(TipoEventoAuditoria.LOGOUT, 'Cierre de sesión')

        assert resultado is None
        assert 'evento=LOGOUT' in log_seguridad.text
        assert 'No se pudo guardar el evento LOGOUT' in log_seguridad.text


class TestRegistroDeLimitePeticiones:
    def _request(self, usuario=None, ip='10.9.9.9', ruta='/api/perfil/'):
        from django.contrib.auth.models import AnonymousUser
        from django.test import RequestFactory

        request = RequestFactory().get(ruta, REMOTE_ADDR=ip)
        request.user = usuario or AnonymousUser()
        return request

    def test_identifica_al_usuario_rechazado_y_el_motivo(self, jugador):
        AuditoriaService.registrar_limite_peticiones(self._request(jugador), 'Superaste el límite de solicitudes.')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES)
        assert log.usuario == jugador
        assert log.accion == 'GET /api/perfil/'
        assert log.detalle == 'Superaste el límite de solicitudes.'

    def test_repeticiones_dentro_de_la_ventana_no_se_duplican(self, jugador):
        for _ in range(10):
            AuditoriaService.registrar_limite_peticiones(self._request(jugador))

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES).count() == 1

    def test_distingue_usuario_y_ruta_desde_la_misma_ip(self, jugador, dueno):
        AuditoriaService.registrar_limite_peticiones(self._request(jugador))
        AuditoriaService.registrar_limite_peticiones(self._request(dueno))
        AuditoriaService.registrar_limite_peticiones(self._request(jugador, ruta='/api/auditoria/'))

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES).count() == 3

    def test_al_vencer_la_ventana_se_vuelve_a_registrar(self, jugador):
        from django.core.cache import cache

        AuditoriaService.registrar_limite_peticiones(self._request(jugador))
        cache.clear()
        AuditoriaService.registrar_limite_peticiones(self._request(jugador))

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.LIMITE_PETICIONES).count() == 2


class TestSinCredencialesEnLosRegistros:
    def test_oculta_claves_sensibles_de_un_diccionario(self):
        texto = AuditoriaService.depurar({'email': 'a@b.com', 'password': 'Secreta#1', 'refresh': 'abc'})

        assert 'Secreta#1' not in texto
        assert 'abc' not in texto
        assert 'email=a@b.com' in texto

    def test_oculta_jwt_y_pares_clave_valor(self):
        jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJ1c3VhcmlvX2lkIjoxfQ.firma-del-token'

        texto = AuditoriaService.depurar(f'Bearer {jwt} password=Secreta#1 token: xyz')

        assert jwt not in texto
        assert 'Secreta#1' not in texto
        assert 'xyz' not in texto

    def test_elimina_saltos_de_linea_para_evitar_inyeccion_en_el_log(self):
        texto = AuditoriaService.depurar('linea uno\r\n2026-01-01 | INFO | seguridad | evento falso')

        assert '\n' not in texto
        assert '\r' not in texto

    def test_el_registro_persistido_queda_depurado(self, rbac, log_seguridad):
        AuditoriaService.registrar(
            TipoEventoAuditoria.LOGIN_FALLIDO, 'Login', detalle={'email': 'x@y.com', 'password': 'NoGuardar#9'},
        )

        assert 'NoGuardar#9' not in LogAuditoria.objects.get().detalle
        assert 'NoGuardar#9' not in log_seguridad.text

    @pytest.mark.parametrize('valor, esperado', [
        ('192.168.0.10', '192.168.0.10'),
        ('2001:db8::1', '2001:db8::1'),
        ('no-es-una-ip', None),
        (None, None),
    ])
    def test_la_ip_invalida_no_se_persiste(self, valor, esperado):
        request = mock.Mock(META={'REMOTE_ADDR': valor} if valor else {})

        assert AuditoriaService.ip_de_request(request) == esperado


@pytest.fixture
def logs(jugador, dueno, complejo, complejo_ajeno):
    def _crear(tipo, usuario=None, complejo_log=None, ip=None, dias_atras=0):
        log = AuditoriaService.registrar(tipo, 'Evento de prueba', usuario=usuario, complejo=complejo_log, ip_origen=ip)
        fecha = timezone.now() - timedelta(days=dias_atras)
        LogAuditoria.objects.filter(pk=log.pk).update(fecha_creacion=fecha)
        return log

    return {
        'login_jugador': _crear(TipoEventoAuditoria.LOGIN_EXITOSO, jugador, ip='10.0.0.1', dias_atras=10),
        'fallido_jugador': _crear(TipoEventoAuditoria.LOGIN_FALLIDO, jugador, ip='10.0.0.2', dias_atras=5),
        'excepcion_propia': _crear(TipoEventoAuditoria.ALTA_EXCEPCION, dueno, complejo, ip='10.0.0.3', dias_atras=2),
        'contrato_ajeno': _crear(TipoEventoAuditoria.CAMBIO_CONTRATO, None, complejo_ajeno, dias_atras=0),
    }


def _ids(respuesta):
    return {log['id'] for log in respuesta.json()['results']}


class TestEndpointAuditoria:
    def test_superadmin_lista_paginado(self, superadmin, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert set(cuerpo) == {'count', 'next', 'previous', 'results'}
        assert cuerpo['count'] == 4
        assert set(cuerpo['results'][0]) == {
            'id', 'fecha_accion', 'tipo_evento', 'tipo_evento_nombre', 'accion', 'detalle',
            'usuario', 'usuario_email', 'complejo', 'complejo_nombre', 'ip_origen',
        }

    def test_ordena_del_mas_reciente_al_mas_antiguo(self, superadmin, logs, cliente_de):
        resultados = cliente_de(superadmin).get(URL).json()['results']

        assert resultados[0]['id'] == logs['contrato_ajeno'].id
        assert resultados[-1]['id'] == logs['login_jugador'].id

    def test_pagina_de_a_20(self, superadmin, cliente_de):
        for numero in range(25):
            AuditoriaService.registrar(TipoEventoAuditoria.LOGOUT, f'Evento {numero}')

        cuerpo = cliente_de(superadmin).get(URL).json()

        assert cuerpo['count'] == 25
        assert len(cuerpo['results']) == 20
        assert cuerpo['next'] is not None

    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno'])
    def test_otros_roles_reciben_403(self, request, cliente_de, fixture_usuario):
        usuario = request.getfixturevalue(fixture_usuario)

        respuesta = cliente_de(usuario).get(URL)

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert LogAuditoria.objects.filter(
            tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO, usuario=usuario, accion=f'GET {URL}',
        ).exists()

    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_filtra_por_tipo_de_evento(self, superadmin, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'tipo_evento': TipoEventoAuditoria.LOGIN_FALLIDO})

        assert _ids(respuesta) == {logs['fallido_jugador'].id}

    def test_filtra_por_usuario(self, superadmin, jugador, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'usuario': jugador.id})

        assert _ids(respuesta) == {logs['login_jugador'].id, logs['fallido_jugador'].id}

    def test_filtra_por_complejo(self, superadmin, complejo_ajeno, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'complejo': complejo_ajeno.id})

        assert _ids(respuesta) == {logs['contrato_ajeno'].id}

    def test_filtra_por_ip(self, superadmin, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'ip_origen': '10.0.0.3'})

        assert _ids(respuesta) == {logs['excepcion_propia'].id}

    def test_filtra_por_rango_de_fechas_inclusivo(self, superadmin, logs, cliente_de):
        hoy = timezone.localdate()
        respuesta = cliente_de(superadmin).get(URL, {
            'fecha_desde': (hoy - timedelta(days=5)).isoformat(),
            'fecha_hasta': (hoy - timedelta(days=2)).isoformat(),
        })

        assert _ids(respuesta) == {logs['fallido_jugador'].id, logs['excepcion_propia'].id}

    def test_solo_fecha_desde(self, superadmin, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'fecha_desde': timezone.localdate().isoformat()})

        assert _ids(respuesta) == {logs['contrato_ajeno'].id}

    def test_combina_filtros(self, superadmin, jugador, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {
            'usuario': jugador.id, 'tipo_evento': TipoEventoAuditoria.LOGIN_EXITOSO,
        })

        assert _ids(respuesta) == {logs['login_jugador'].id}

    def test_rango_sin_eventos_devuelve_lista_vacia(self, superadmin, logs, cliente_de):
        respuesta = cliente_de(superadmin).get(URL, {'fecha_desde': '2020-01-01', 'fecha_hasta': '2020-01-31'})

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['count'] == 0

    def test_incluye_el_ultimo_instante_de_fecha_hasta(self, superadmin, rbac, cliente_de):
        log = AuditoriaService.registrar(TipoEventoAuditoria.LOGOUT, 'Al filo de la medianoche')
        fin_del_dia = datetime(2026, 3, 10, 23, 59, 59, tzinfo=timezone.get_current_timezone())
        LogAuditoria.objects.filter(pk=log.pk).update(fecha_creacion=fin_del_dia)

        respuesta = cliente_de(superadmin).get(URL, {'fecha_desde': '2026-03-10', 'fecha_hasta': '2026-03-10'})

        assert _ids(respuesta) == {log.id}

    @pytest.mark.parametrize('parametros, campo', [
        ({'tipo_evento': '99'}, 'tipo_evento'),
        ({'usuario': 'abc'}, 'usuario'),
        ({'ip_origen': 'no-ip'}, 'ip_origen'),
        ({'fecha_desde': '10/03/2026'}, 'fecha_desde'),
        ({'fecha_desde': '2026-03-10', 'fecha_hasta': '2026-03-01'}, 'fecha_hasta'),
    ])
    def test_filtros_invalidos_responden_400(self, superadmin, cliente_de, parametros, campo):
        respuesta = cliente_de(superadmin).get(URL, parametros)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['error'] is True
        assert campo in respuesta.json()['detail']

    def test_no_admite_escritura(self, superadmin, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, {'accion': 'falsa'}, format='json')

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
