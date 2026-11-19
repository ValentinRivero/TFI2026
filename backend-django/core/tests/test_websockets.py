import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import time, timedelta
from unittest import mock

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from config.asgi import application
from core.consumers import CIERRE_COMPLEJO_NO_DISPONIBLE
from core.models import DiaSemana, EstadoContrato, EstadoUsuario, Reserva
from core.services import DifusionGrillaService, ReservaService, grupo_de_complejo
from core.ws_auth import JWTAuthMiddleware


def _origen_permitido():
    """Origen de un host de ALLOWED_HOSTS, la misma lista con la que asgi.py arma el validador de origen."""
    permitido = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
    host = 'localhost' if permitido == '*' else permitido.lstrip('.')
    return f'http://{host}'.encode()


def _conectar(complejo_id, token=None, origen=None):
    ruta = f'/ws/complejos/{complejo_id}/disponibilidad/'
    if token is not None:
        ruta += f'?token={token}'
    encabezados = [(b'origin', origen or _origen_permitido())]
    return WebsocketCommunicator(application, ruta, headers=encabezados)


def _access(usuario):
    from core.serializers_auth import TokenConRolSerializer

    return str(TokenConRolSerializer.get_token(usuario).access_token)


def _correr(corrutina):
    """Cada prueba corre en un único loop: el comunicador no sobrevive entre llamadas a async_to_sync."""
    return async_to_sync(corrutina)()


@pytest.fixture(autouse=True)
def capa_de_canales_nueva(settings):
    """
    El InMemoryChannelLayer guarda colas atadas a un loop: cada prueba arranca con una capa limpia. Redefinir
    CHANNEL_LAYERS dispara setting_changed, con el que Channels descarta las capas creadas.
    """
    settings.CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def log_difusion(caplog):
    """El logger core no propaga a la raíz: se le engancha el handler de captura de pytest."""
    logger = logging.getLogger('core')
    logger.addHandler(caplog.handler)
    caplog.set_level(logging.WARNING, logger='core')
    yield caplog
    logger.removeHandler(caplog.handler)


class TestConexion:
    def test_un_anonimo_se_conecta_a_un_complejo_publico(self, complejo):
        async def prueba():
            ws = _conectar(complejo.id)
            conectado, _ = await ws.connect()
            assert conectado
            assert await ws.receive_nothing()
            await ws.disconnect()

        _correr(prueba)

    @pytest.mark.parametrize('token', ['', 'no-es-un-jwt', 'eyJhbGciOiJIUzI1NiJ9.eyJ1c3VhcmlvX2lkIjoiMSJ9.firma'])
    def test_un_token_ausente_o_invalido_no_cierra_la_conexion(self, complejo, token):
        async def prueba():
            ws = _conectar(complejo.id, token=token)
            conectado, _ = await ws.connect()
            assert conectado
            await ws.disconnect()

        _correr(prueba)

    def test_un_usuario_con_token_valido_tambien_se_conecta(self, complejo, jugador):
        token = _access(jugador)

        async def prueba():
            ws = _conectar(complejo.id, token=token)
            conectado, _ = await ws.connect()
            assert conectado
            await ws.disconnect()

        _correr(prueba)

    @pytest.mark.parametrize('estado_contrato', [EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA])
    def test_rechaza_un_complejo_sin_contrato_activo(self, complejo, estado_contrato):
        complejo.estado_contrato = estado_contrato
        complejo.save()

        async def prueba():
            conectado, codigo = await _conectar(complejo.id).connect()
            assert not conectado
            assert codigo == CIERRE_COMPLEJO_NO_DISPONIBLE

        _correr(prueba)

    def test_rechaza_un_complejo_dado_de_baja_o_inexistente(self, complejo):
        complejo.desactivar()

        async def prueba():
            for complejo_id in (complejo.id, 999999):
                conectado, codigo = await _conectar(complejo_id).connect()
                assert not conectado and codigo == CIERRE_COMPLEJO_NO_DISPONIBLE

        _correr(prueba)

    def test_rechaza_conexiones_desde_otro_origen(self, complejo):
        async def prueba():
            conectado, _ = await _conectar(complejo.id, origen=b'https://sitio-ajeno.example').connect()
            assert not conectado

        _correr(prueba)

    def test_ignora_los_mensajes_del_cliente(self, complejo):
        async def prueba():
            ws = _conectar(complejo.id)
            await ws.connect()
            await ws.send_to(text_data='{"event": "grilla_actualizada", "cancha_id": 1}')
            await ws.send_to(text_data='esto no es JSON')
            await ws.send_to(bytes_data=b'\x00\x01')
            assert await ws.receive_nothing()
            # La conexión sigue abierta y responde a una difusión posterior.
            await database_sync_to_async(DifusionGrillaService.publicar)(complejo.id, {'event': 'grilla_actualizada'})
            assert await ws.receive_json_from() == {'event': 'grilla_actualizada'}
            await ws.disconnect()

        _correr(prueba)


class TestIdentificacionPermisiva:
    def _usuario_tras_middleware(self, query):
        capturado = {}

        async def interna(scope, receive, send):
            capturado.update(scope)

        async def prueba():
            await JWTAuthMiddleware(interna)({'type': 'websocket', 'query_string': query}, None, None)

        _correr(prueba)
        return capturado['user']

    def test_identifica_al_usuario_de_un_access_valido(self, jugador):
        usuario = self._usuario_tras_middleware(f'token={_access(jugador)}'.encode())

        assert usuario.pk == jugador.pk and usuario.is_authenticated

    def test_convierte_el_usuario_id_de_texto_a_entero(self, jugador):
        token = AccessToken(_access(jugador))

        assert token['usuario_id'] == str(jugador.pk)
        assert self._usuario_tras_middleware(f'token={token}'.encode()).pk == jugador.pk

    def test_sin_token_queda_anonimo(self, db):
        assert isinstance(self._usuario_tras_middleware(b''), AnonymousUser)
        assert isinstance(self._usuario_tras_middleware(b'otro=1'), AnonymousUser)

    def test_un_token_vencido_queda_anonimo(self, jugador):
        token = AccessToken(_access(jugador))
        token.set_exp(lifetime=-timedelta(minutes=1))

        assert isinstance(self._usuario_tras_middleware(f'token={token}'.encode()), AnonymousUser)

    def test_un_refresh_no_sirve_como_access(self, jugador):
        refresh = RefreshToken.for_user(jugador)

        assert isinstance(self._usuario_tras_middleware(f'token={refresh}'.encode()), AnonymousUser)

    def test_un_usuario_id_no_numerico_queda_anonimo(self, jugador):
        token = AccessToken(_access(jugador))
        token['usuario_id'] = 'abc'

        assert isinstance(self._usuario_tras_middleware(f'token={token}'.encode()), AnonymousUser)

    @pytest.mark.parametrize('estado', [EstadoUsuario.SUSPENDIDO, EstadoUsuario.BAJA])
    def test_una_cuenta_no_activa_queda_anonima(self, jugador, estado):
        token = _access(jugador)
        jugador.estado = estado
        jugador.save()

        assert isinstance(self._usuario_tras_middleware(f'token={token}'.encode()), AnonymousUser)


class TestDifusionEnTiempoReal:
    def _reservar(self, jugador, cancha, fecha, captura):
        with captura(execute=True):
            return ReservaService.crear_reserva(
                {'cancha': cancha, 'fecha_turno': fecha, 'hora_inicio': time(20, 0)}, jugador, None,
            )

    def test_una_reserva_confirmada_llega_a_las_grillas_abiertas_sin_datos_personales(
        self, reloj, jugador, complejo, cancha, django_capture_on_commit_callbacks,
    ):
        martes = reloj.return_value.date() + timedelta(days=1)

        async def prueba():
            ws = _conectar(complejo.id)
            await ws.connect()
            await database_sync_to_async(self._reservar)(jugador, cancha, martes, django_capture_on_commit_callbacks)
            evento = await ws.receive_json_from()
            await ws.disconnect()
            return evento

        evento = _correr(prueba)

        # La igualdad exacta asegura que no viaja ningún otro campo: ni usuario, ni contacto, ni precio.
        assert evento == {
            'event': 'grilla_actualizada', 'cancha_id': cancha.id, 'fecha_desde': martes.isoformat(),
            'fecha_hasta': martes.isoformat(), 'hora_inicio': '20:00:00', 'hora_fin': '21:00:00',
        }
        assert 'jugador@talibre.test' not in json.dumps(evento) and 'Jugador' not in json.dumps(evento)

    def test_solo_avisa_a_las_grillas_de_ese_complejo(
        self, reloj, jugador, complejo, complejo_ajeno, cancha, django_capture_on_commit_callbacks,
    ):
        martes = reloj.return_value.date() + timedelta(days=1)

        async def prueba():
            propio, ajeno = _conectar(complejo.id), _conectar(complejo_ajeno.id)
            await propio.connect()
            await ajeno.connect()
            await database_sync_to_async(self._reservar)(jugador, cancha, martes, django_capture_on_commit_callbacks)
            assert (await propio.receive_json_from())['cancha_id'] == cancha.id
            assert await ajeno.receive_nothing()
            await propio.disconnect()
            await ajeno.disconnect()

        _correr(prueba)

    def test_varias_grillas_abiertas_reciben_el_mismo_evento(self, complejo):
        async def prueba():
            clientes = [_conectar(complejo.id) for _ in range(3)]
            for ws in clientes:
                await ws.connect()
            await database_sync_to_async(DifusionGrillaService.publicar)(complejo.id, {'event': 'grilla_actualizada'})
            for ws in clientes:
                assert await ws.receive_json_from() == {'event': 'grilla_actualizada'}
                await ws.disconnect()

        _correr(prueba)

    def test_una_excepcion_se_anuncia_con_su_rango(self, reloj, dueno, complejo, cliente_de, django_capture_on_commit_callbacks):
        desde = reloj.return_value.date() + timedelta(days=3)
        datos = {
            'complejo': complejo.id, 'cancha': None, 'fecha_inicio': desde.isoformat(),
            'fecha_fin': (desde + timedelta(days=2)).isoformat(), 'es_dia_completo': 1, 'tipo_motivo': 3,
        }

        def alta():
            with django_capture_on_commit_callbacks(execute=True):
                return cliente_de(dueno).post('/api/excepciones/', datos, format='json').status_code

        async def prueba():
            ws = _conectar(complejo.id)
            await ws.connect()
            assert await database_sync_to_async(alta)() == status.HTTP_201_CREATED
            evento = await ws.receive_json_from()
            await ws.disconnect()
            return evento

        evento = _correr(prueba)

        assert evento['cancha_id'] is None and evento['hora_inicio'] is None
        assert (evento['fecha_desde'], evento['fecha_hasta']) == (datos['fecha_inicio'], datos['fecha_fin'])

    def test_no_se_anuncia_nada_si_la_transaccion_se_revierte(
        self, reloj, jugador, complejo, cancha, django_capture_on_commit_callbacks,
    ):
        martes = reloj.return_value.date() + timedelta(days=1)

        def reservar_y_revertir():
            with django_capture_on_commit_callbacks(execute=True) as pendientes:
                with pytest.raises(RuntimeError), transaction.atomic():
                    ReservaService.crear_reserva(
                        {'cancha': cancha, 'fecha_turno': martes, 'hora_inicio': time(20, 0)}, jugador, None,
                    )
                    raise RuntimeError('falla posterior dentro de la misma transacción')
            return pendientes

        async def prueba():
            ws = _conectar(complejo.id)
            await ws.connect()
            pendientes = await database_sync_to_async(reservar_y_revertir)()
            assert pendientes == []
            assert await ws.receive_nothing()
            await ws.disconnect()

        _correr(prueba)
        assert not Reserva.objects.exists()

    @pytest.mark.parametrize('estado_contrato', [EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA])
    def test_suspender_el_contrato_cierra_las_grillas_abiertas(
        self, superadmin, complejo, complejo_ajeno, cliente_de, django_capture_on_commit_callbacks, estado_contrato,
    ):
        def suspender():
            with django_capture_on_commit_callbacks(execute=True):
                return cliente_de(superadmin).patch(
                    f'/api/contratos/{complejo.id}/', {'estado_contrato': estado_contrato}, format='json',
                ).status_code

        async def prueba():
            afectada, otra = _conectar(complejo.id), _conectar(complejo_ajeno.id)
            await afectada.connect()
            await otra.connect()
            assert await database_sync_to_async(suspender)() == status.HTTP_200_OK
            assert await afectada.receive_output() == {'type': 'websocket.close', 'code': CIERRE_COMPLEJO_NO_DISPONIBLE}
            assert await otra.receive_nothing()
            await otra.disconnect()

        _correr(prueba)

    def test_un_cambio_de_operatoria_llega_a_las_grillas_abiertas(
        self, reloj, dueno, complejo, cancha, cliente_de, django_capture_on_commit_callbacks,
    ):
        def cambiar_precio():
            with django_capture_on_commit_callbacks(execute=True):
                return cliente_de(dueno).patch(
                    f'/api/canchas/{cancha.id}/', {'precio_base': '41000.00'}, format='json',
                ).status_code

        async def prueba():
            ws = _conectar(complejo.id)
            await ws.connect()
            assert await database_sync_to_async(cambiar_precio)() == status.HTTP_200_OK
            evento = await ws.receive_json_from()
            await ws.disconnect()
            return evento

        evento = _correr(prueba)

        assert evento == {
            'event': 'grilla_actualizada', 'cancha_id': cancha.id,
            'fecha_desde': reloj.return_value.date().isoformat(), 'fecha_hasta': None,
            'hora_inicio': None, 'hora_fin': None,
        }

    def test_publica_al_grupo_del_complejo(self, complejo):
        capa = mock.MagicMock()
        capa.group_send = mock.AsyncMock()

        with mock.patch('core.services.get_channel_layer', return_value=capa):
            DifusionGrillaService.publicar(complejo.id, {'event': 'grilla_actualizada'})

        capa.group_send.assert_awaited_once_with(
            f'complejo_{complejo.id}', {'type': 'grilla.actualizada', 'evento': {'event': 'grilla_actualizada'}},
        )
        assert grupo_de_complejo(str(complejo.id)) == f'complejo_{complejo.id}'

    def test_una_falla_del_channel_layer_no_rompe_la_operacion_confirmada(
        self, reloj, jugador, cliente_de, cancha, log_difusion, django_capture_on_commit_callbacks,
    ):
        capa = mock.MagicMock()
        capa.group_send = mock.AsyncMock(side_effect=ConnectionError('Redis no responde'))
        martes = reloj.return_value.date() + timedelta(days=1)

        with mock.patch('core.services.get_channel_layer', return_value=capa):
            with django_capture_on_commit_callbacks(execute=True):
                respuesta = cliente_de(jugador).post('/api/reservas/', {
                    'cancha': cancha.id, 'fecha_turno': martes.isoformat(), 'hora_inicio': '20:00',
                }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert Reserva.objects.count() == 1
        capa.group_send.assert_awaited_once()
        assert 'No se pudo difundir la grilla del complejo' in log_difusion.text

    def test_desde_codigo_asincrono_el_envio_no_bloquea_el_loop(self, complejo):
        async def prueba():
            ws = _conectar(complejo.id)
            await ws.connect()
            DifusionGrillaService.publicar(complejo.id, {'event': 'grilla_actualizada', 'cancha_id': 7})
            assert await ws.receive_json_from() == {'event': 'grilla_actualizada', 'cancha_id': 7}
            await ws.disconnect()

        _correr(prueba)

    def test_desde_codigo_asincrono_una_falla_queda_registrada(self, complejo, log_difusion):
        capa = mock.MagicMock()
        capa.group_send = mock.AsyncMock(side_effect=ConnectionError('Redis no responde'))

        async def prueba():
            with mock.patch('core.services.get_channel_layer', return_value=capa):
                DifusionGrillaService.publicar(complejo.id, {'event': 'grilla_actualizada'})
            for _ in range(3):
                await asyncio.sleep(0)

        _correr(prueba)

        capa.group_send.assert_awaited_once()
        assert 'No se pudo difundir la grilla del complejo' in log_difusion.text
        assert 'Redis no responde' in log_difusion.text

    def test_sin_capa_configurada_registra_y_sigue(self, complejo, log_difusion):
        with mock.patch('core.services.get_channel_layer', return_value=None):
            DifusionGrillaService.publicar(complejo.id, {'event': 'grilla_actualizada'})

        assert 'No se pudo difundir' in log_difusion.text


class TestConfiguracionDeCapas:
    def test_las_pruebas_usan_canales_y_cache_en_memoria(self):
        assert settings.CHANNEL_LAYERS['default']['BACKEND'] == 'channels.layers.InMemoryChannelLayer'
        assert settings.CACHES['default']['BACKEND'] == 'django.core.cache.backends.locmem.LocMemCache'

    @pytest.mark.parametrize('redis_url, canales, cache', [
        ('redis://localhost:6379/0', 'channels_redis.core.RedisChannelLayer',
         'django.core.cache.backends.redis.RedisCache'),
        ('', 'channels.layers.InMemoryChannelLayer', 'django.core.cache.backends.locmem.LocMemCache'),
    ], ids=['con-redis', 'sin-redis'])
    def test_redis_url_define_canales_y_cache(self, redis_url, canales, cache):
        codigo = (
            'import json\n'
            'from config import settings as s\n'
            "print(json.dumps([s.CHANNEL_LAYERS['default']['BACKEND'], s.CACHES['default']['BACKEND'], "
            "s.CACHES['default'].get('LOCATION')]))\n"
        )
        entorno = {**os.environ, 'REDIS_URL': redis_url}
        entorno.setdefault('DJANGO_SECRET_KEY', 'prueba-0123456789abcdef0123456789abcdef')
        entorno.setdefault('JWT_SIGNING_KEY', 'prueba-fedcba9876543210fedcba9876543210')

        salida = subprocess.run(
            [sys.executable, '-c', codigo], cwd=settings.BASE_DIR, env=entorno,
            capture_output=True, text=True, timeout=120, check=True,
        )

        backend_canales, backend_cache, ubicacion = json.loads(salida.stdout.strip().splitlines()[-1])
        assert (backend_canales, backend_cache) == (canales, cache)
        assert ubicacion == (redis_url or None)
