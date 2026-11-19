"""
Recordatorio del turno próximo (comando, verificación transparente del jugador y deduplicación por clave) y reporte
de estado del servidor para los superadministradores.
"""
import json
import threading
import time
from datetime import datetime, time as hora, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status

from conftest import HOY_CONGELADO
from core import node_client
from core.models import DiaSemana, EstadoReserva, EstadoUsuario
from core.services import (
    CATEGORIA_AVISO_RESERVAS,
    CATEGORIA_AVISO_SISTEMA,
    PRIORIDAD_AVISO_NORMAL,
    PRIORIDAD_AVISO_URGENTE,
    AvisoComplejoService,
    EstadoSistemaService,
    RecordatorioService,
)
from core.tests.test_avisos_node import CLAVE, NodeSimulado

MARTES = HOY_CONGELADO + timedelta(days=1)


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, hora(8, 0), hora(23, 0))
    return cancha


@pytest.fixture
def reserva(reloj, cancha, crear_reserva):
    """El turno del martes 17/11 a las 14:00. El reloj queda 23 horas antes, dentro de la ventana de 24 horas."""
    reloj.return_value = timezone.make_aware(datetime.combine(HOY_CONGELADO, hora(15, 0)))
    return crear_reserva(cancha, MARTES, hora(14, 0), hora(15, 0), estado=EstadoReserva.CONFIRMADA)


@pytest.fixture
def entregados():
    with mock.patch.object(AvisoComplejoService, 'entregar') as entregar:
        yield entregar


@pytest.fixture
def commit_inmediato():
    """Los avisos programados con `transaction.on_commit` salen en el acto: la prueba no corre en una transacción real."""
    with mock.patch('core.services.transaction.on_commit', side_effect=lambda funcion, robust=False: funcion()):
        yield


@pytest.fixture
def en_el_acto():
    """La entrega en segundo plano corre en el mismo hilo, para poder verificarla."""
    with mock.patch.object(
        AvisoComplejoService, 'entregar_en_segundo_plano',
        side_effect=lambda avisos: [AvisoComplejoService.entregar(aviso) for aviso in avisos],
    ) as parche:
        yield parche


def _avisos(entregar):
    return [llamada.args[0] for llamada in entregar.call_args_list]


class TestRecordatorioDeTurno:
    def test_avisa_al_titular_con_una_clave_por_reserva(self, jugador, reserva, entregados):
        assert RecordatorioService.emitir_pendientes() == 1

        (aviso,) = _avisos(entregados)
        assert aviso['usuario_id'] == jugador.id and aviso['complejo_id'] is None
        assert aviso['clave_unica'] == f'recordatorio-reserva-{reserva.id}'
        assert (aviso['categoria'], aviso['prioridad']) == (CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL)
        assert aviso['mensaje'] == (
            f'Recordatorio: tenés turno mañana a las 14:00 en Complejo Propio (Cancha 1, reserva id {reserva.id}).'
        )

    def test_el_mismo_dia_dice_hoy(self, reloj, reserva, entregados):
        reloj.return_value = reloj.return_value.replace(day=17, hour=9)

        RecordatorioService.emitir_pendientes()

        assert 'hoy a las 14:00' in _avisos(entregados)[0]['mensaje']

    @pytest.mark.parametrize('estado', [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA])
    def test_recuerda_las_reservas_activas(self, reserva, entregados, estado):
        reserva.estado = estado
        reserva.save()

        assert RecordatorioService.emitir_pendientes() == 1

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE,
        EstadoReserva.COMPLETADA,
    ])
    def test_no_recuerda_lo_cancelado_ni_lo_ya_resuelto(self, reserva, entregados, estado):
        reserva.estado = estado
        reserva.save()

        assert RecordatorioService.emitir_pendientes() == 0
        entregados.assert_not_called()

    def test_no_recuerda_un_turno_fuera_de_la_ventana(self, reloj, reserva, entregados):
        reloj.return_value = reloj.return_value.replace(day=16, hour=13)

        assert RecordatorioService.emitir_pendientes() == 0

    def test_la_ventana_la_define_la_configuracion(self, reloj, reserva, entregados, settings):
        reloj.return_value = reloj.return_value.replace(day=16, hour=13)
        settings.RECORDATORIO_HORAS_ANTICIPACION = 48

        assert RecordatorioService.emitir_pendientes() == 1

    def test_no_recuerda_un_turno_que_ya_empezo(self, reloj, reserva, entregados):
        reloj.return_value = reloj.return_value.replace(day=17, hour=14, minute=30)

        assert RecordatorioService.emitir_pendientes() == 0

    def test_no_recuerda_a_una_cuenta_dada_de_baja_ni_a_una_reserva_manual(
        self, jugador, reserva, cancha, crear_reserva, entregados,
    ):
        crear_reserva(cancha, MARTES, hora(16, 0), hora(17, 0), usuario=None)
        jugador.estado = EstadoUsuario.BAJA
        jugador.save()

        assert RecordatorioService.emitir_pendientes() == 0

    def test_el_mensaje_no_tiene_datos_personales(self, jugador, reserva, entregados):
        RecordatorioService.emitir_pendientes()

        mensaje = _avisos(entregados)[0]['mensaje']
        assert jugador.email not in mensaje and jugador.nombre_completo not in mensaje

    def test_el_comando_emite_los_recordatorios_pendientes(self, reserva, entregados):
        salida = StringIO()

        call_command('emitir_recordatorios_reservas', stdout=salida)

        assert 'Recordatorios enviados a backend-node: 1' in salida.getvalue()
        assert len(_avisos(entregados)) == 1

    def test_correr_el_comando_dos_veces_repite_la_misma_clave_para_que_node_descarte_el_duplicado(
        self, reserva, entregados,
    ):
        call_command('emitir_recordatorios_reservas', stdout=StringIO())
        call_command('emitir_recordatorios_reservas', stdout=StringIO())

        claves = {aviso['clave_unica'] for aviso in _avisos(entregados)}
        assert claves == {f'recordatorio-reserva-{reserva.id}'}


class TestVerificacionTransparenteDelJugador:
    def test_consultar_las_reservas_propias_dispara_el_recordatorio(
        self, jugador, reserva, cliente_de, entregados, en_el_acto,
    ):
        respuesta = cliente_de(jugador).get('/api/reservas/mias/')

        assert respuesta.status_code == status.HTTP_200_OK
        (aviso,) = _avisos(entregados)
        assert aviso['usuario_id'] == jugador.id

    def test_consultar_la_grilla_de_un_complejo_tambien(self, jugador, reserva, complejo, cliente_de, entregados, en_el_acto):
        respuesta = cliente_de(jugador).get(f'/api/complejos/{complejo.id}/grilla/', {'fecha': MARTES.isoformat()})

        assert respuesta.status_code == status.HTTP_200_OK
        assert len(_avisos(entregados)) == 1

    def test_la_grilla_sin_sesion_no_verifica_nada(self, reserva, complejo, cliente, entregados, en_el_acto):
        respuesta = cliente.get(f'/api/complejos/{complejo.id}/grilla/', {'fecha': MARTES.isoformat()})

        assert respuesta.status_code == status.HTTP_200_OK
        entregados.assert_not_called()

    def test_solo_verifica_una_vez_por_intervalo(self, jugador, reserva, cliente_de, entregados, en_el_acto, settings):
        api = cliente_de(jugador)

        api.get('/api/reservas/mias/')
        api.get('/api/reservas/mias/')
        assert len(_avisos(entregados)) == 1

        cache.clear()
        api.get('/api/reservas/mias/')
        assert len(_avisos(entregados)) == 2

    def test_una_falla_del_recordatorio_no_rompe_la_consulta(self, jugador, reserva, cliente_de):
        with mock.patch.object(RecordatorioService, 'emitir_pendientes', side_effect=RuntimeError('falla')):
            respuesta = cliente_de(jugador).get('/api/reservas/mias/')

        assert respuesta.status_code == status.HTTP_200_OK

    def test_un_jugador_sin_turnos_proximos_no_emite_nada(self, jugador, cliente_de, entregados, en_el_acto):
        assert cliente_de(jugador).get('/api/reservas/mias/').status_code == status.HTTP_200_OK
        entregados.assert_not_called()

    def test_la_entrega_en_segundo_plano_no_bloquea_y_llega(self, entregados):
        aviso = {'complejo_id': None, 'usuario_id': 1, 'categoria': 1, 'prioridad': 1, 'mensaje': 'x'}

        AvisoComplejoService.entregar_en_segundo_plano([aviso])

        limite = time.monotonic() + 2
        while not entregados.called and time.monotonic() < limite:
            time.sleep(0.01)
        entregados.assert_called_once_with(aviso)
        assert threading.current_thread().name != 'avisos'


class TestRecordatorioHaciaNode:
    def test_viaja_con_la_clave_de_idempotencia(self, reserva, settings):
        with NodeSimulado() as node:
            settings.NODE_API_URL, settings.INTERNAL_API_KEY = node.url, CLAVE
            RecordatorioService.emitir_pendientes()
            RecordatorioService.emitir_pendientes()

        assert [pedido['cuerpo']['clave_unica'] for pedido in node.pedidos] == [f'recordatorio-reserva-{reserva.id}'] * 2
        assert node.pedidos[0]['cuerpo']['usuario_id'] == reserva.usuario_id


class _NodeConEstado:
    """backend-node mínimo que responde el estado interno por GET."""

    def __init__(self, cuerpo, estado=200):
        self.pedidos = []
        yo = self

        class Manejador(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                yo.pedidos.append({'ruta': self.path, 'clave': self.headers.get('X-Internal-Key')})
                contenido = json.dumps(cuerpo).encode()
                self.send_response(estado)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(contenido)))
                self.end_headers()
                self.wfile.write(contenido)

            def log_message(self, *args):
                pass

        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), Manejador)
        self.url = f'http://127.0.0.1:{self.servidor.server_port}'
        threading.Thread(target=self.servidor.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.servidor.shutdown()
        self.servidor.server_close()


ESTADO_NORMAL = {
    'estado': 'ok', 'motivos': [],
    'metricas': {
        'memoria_rss_mb': 120, 'memoria_heap_mb': 40, 'latencia_mongo_ms': 8, 'eventos_24h': 15,
        'notificaciones_sin_leer': 3, 'fallas_externas_recientes': 0, 'uptime_s': 3600,
    },
}


@pytest.fixture
def sin_node(settings):
    settings.NODE_API_URL, settings.INTERNAL_API_KEY = '', ''


class TestClienteDeEstado:
    def test_consulta_el_estado_interno_con_la_clave(self, settings):
        with _NodeConEstado(ESTADO_NORMAL) as node:
            settings.NODE_API_URL, settings.INTERNAL_API_KEY = node.url, CLAVE

            estado = node_client.consultar_estado()

        assert estado == ESTADO_NORMAL
        assert node.pedidos == [{'ruta': '/api/interno/estado', 'clave': CLAVE}]

    def test_sin_configuracion_no_intenta_la_consulta(self, sin_node):
        with pytest.raises(node_client.NodeNoConfigurado):
            node_client.consultar_estado()

    def test_una_respuesta_de_error_es_node_no_disponible(self, settings):
        with _NodeConEstado({'error': True}, estado=502) as node:
            settings.NODE_API_URL, settings.INTERNAL_API_KEY = node.url, CLAVE

            with pytest.raises(node_client.NodeNoDisponible, match='HTTP 502'):
                node_client.consultar_estado()


@pytest.mark.django_db
@pytest.mark.usefixtures('commit_inmediato')
class TestReporteDeEstadoDelServidor:
    def test_medicion_normal_sin_node_configurado(self, reloj, jugador, reserva, sin_node):
        reporte = EstadoSistemaService.medir()

        assert reporte['motivos'] == [] and reporte['node'] is None
        assert reporte['reservas_por_jugar'] == 1 and reporte['usuarios_activos'] >= 1

    def test_una_base_lenta_degrada_el_reporte(self, sin_node, settings):
        with mock.patch.object(EstadoSistemaService, '_latencia_bd_ms', return_value=900):
            reporte = EstadoSistemaService.medir()

        assert reporte['motivos'] == ['la base de datos tarda 900 ms (máximo 500 ms)']

    def test_un_node_degradado_aporta_sus_motivos(self, sin_node):
        degradado = {**ESTADO_NORMAL, 'estado': 'degradado', 'motivos': ['5 fallas de servicios externos en 5 min']}
        with mock.patch.object(node_client, 'consultar_estado', return_value=degradado):
            reporte = EstadoSistemaService.medir()

        assert reporte['motivos'] == ['5 fallas de servicios externos en 5 min']

    def test_un_node_que_no_responde_degrada_el_reporte(self, sin_node):
        with mock.patch.object(node_client, 'consultar_estado', side_effect=node_client.NodeNoDisponible('no respondió')):
            reporte = EstadoSistemaService.medir()

        assert reporte['motivos'] == ['backend-node no respondió']

    def test_avisa_a_cada_superadmin_en_la_categoria_sistema(self, reloj, superadmin, crear_usuario, entregados, sin_node):
        otro = crear_usuario('segundo.superadmin@talibre.test', 'SUPERADMIN')
        with mock.patch.object(node_client, 'consultar_estado', return_value=ESTADO_NORMAL):
            EstadoSistemaService.emitir_reporte_estado_servidor()

        (aviso,) = _avisos(entregados)
        assert aviso['usuarios_ids'] == sorted([superadmin.id, otro.id])
        assert (aviso['categoria'], aviso['prioridad']) == (CATEGORIA_AVISO_SISTEMA, PRIORIDAD_AVISO_NORMAL)
        assert aviso['clave_unica'] == 'estado-servidor-2026111610'
        assert 'Estado del servidor: normal.' in aviso['mensaje'] and 'memoria 120 MB, MongoDB 8 ms' in aviso['mensaje']
        assert len(aviso['mensaje']) <= 280

    def test_si_algo_se_degrada_es_urgente_y_dice_por_que(self, superadmin, entregados, sin_node):
        with mock.patch.object(EstadoSistemaService, '_latencia_bd_ms', return_value=900):
            EstadoSistemaService.emitir_reporte_estado_servidor()

        (aviso,) = _avisos(entregados)
        assert aviso['prioridad'] == PRIORIDAD_AVISO_URGENTE
        assert 'degradado' in aviso['mensaje'] and 'la base de datos tarda 900 ms' in aviso['mensaje']

    def test_solo_si_degradado_calla_con_el_sistema_normal(self, superadmin, entregados, sin_node):
        assert EstadoSistemaService.emitir_reporte_estado_servidor(solo_si_degradado=True) is None
        entregados.assert_not_called()

    def test_sin_superadmins_no_emite_nada(self, entregados, sin_node):
        EstadoSistemaService.emitir_reporte_estado_servidor()

        entregados.assert_not_called()

    def test_con_mongo_caido_el_texto_lo_dice(self, superadmin, entregados, sin_node):
        caido = {
            'estado': 'degradado', 'motivos': ['MongoDB no responde'],
            'metricas': {**ESTADO_NORMAL['metricas'], 'latencia_mongo_ms': None},
        }
        with mock.patch.object(node_client, 'consultar_estado', return_value=caido):
            EstadoSistemaService.emitir_reporte_estado_servidor()

        assert 'MongoDB sin conexión' in _avisos(entregados)[0]['mensaje']

    def test_el_comando_emite_y_informa(self, superadmin, entregados, sin_node):
        salida = StringIO()

        call_command('reportar_estado_sistema', stdout=salida)

        assert 'Reporte de estado emitido a los superadministradores (normal).' in salida.getvalue()
        assert len(_avisos(entregados)) == 1

    def test_el_comando_con_solo_degradado_no_emite_si_todo_esta_normal(self, superadmin, entregados, sin_node):
        salida = StringIO()

        call_command('reportar_estado_sistema', '--solo-degradado', stdout=salida)

        assert 'Estado normal: no se emitió ningún aviso.' in salida.getvalue()
        entregados.assert_not_called()
