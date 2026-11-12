import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from rest_framework import status

from core import node_client
from core.services import (
    CATEGORIA_AVISO_RESERVAS,
    PRIORIDAD_AVISO_NORMAL,
    PRIORIDAD_AVISO_URGENTE,
    AvisoComplejoService,
)

CLAVE = 'clave-interna-de-prueba-0123456789abcdef0123456789'
RUTA = '/api/interno/notificaciones'


class NodeSimulado:
    """backend-node real en un hilo: registra cada pedido y responde lo que el test indique."""

    def __init__(self):
        self.pedidos = []
        self.estado = 201
        self.cuerpo = {'id': '6650f1c2a1b2c3d4e5f60718', 'evento': None}
        self.demora = 0
        self.crudo = None
        self.encabezados_extra = {}
        simulado = self

        class Manejador(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                largo = int(self.headers.get('Content-Length', 0))
                simulado.pedidos.append({
                    'ruta': self.path, 'encabezados': dict(self.headers), 'cuerpo': json.loads(self.rfile.read(largo)),
                })
                time.sleep(simulado.demora)
                contenido = simulado.crudo or json.dumps(simulado.cuerpo).encode()
                self.send_response(simulado.estado)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(contenido)))
                for nombre, valor in simulado.encabezados_extra.items():
                    self.send_header(nombre, valor)
                self.end_headers()
                self.wfile.write(contenido)

            def log_message(self, *args):
                pass

        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), Manejador)
        self.url = f'http://127.0.0.1:{self.servidor.server_port}'
        self.hilo = threading.Thread(target=self.servidor.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)

    def __enter__(self):
        self.hilo.start()
        return self

    def __exit__(self, *args):
        self.servidor.shutdown()
        self.servidor.server_close()


@pytest.fixture
def node(settings):
    with NodeSimulado() as simulado:
        settings.NODE_API_URL = simulado.url
        settings.INTERNAL_API_KEY = CLAVE
        yield simulado


@pytest.fixture
def registro_de_avisos(caplog):
    # El logger `core` no propaga a la raíz: se le agrega el handler de captura mientras dura el test.
    logger = logging.getLogger('core')
    logger.addHandler(caplog.handler)
    caplog.set_level(logging.WARNING, logger='core')
    yield caplog
    logger.removeHandler(caplog.handler)


def _aviso(**cambios):
    aviso = {
        'complejo_id': 4, 'usuario_id': None, 'categoria': CATEGORIA_AVISO_RESERVAS,
        'prioridad': PRIORIDAD_AVISO_URGENTE, 'mensaje': 'La excepción id 9 deja 2 fechas en espera.',
        'referencias': {'excepcion': 9}, 'evento': None,
    }
    aviso.update(cambios)
    return aviso


class TestEntregaANode:
    def test_envia_el_aviso_a_la_ruta_interna_con_la_clave(self, node):
        AvisoComplejoService.entregar(_aviso())

        (pedido,) = node.pedidos
        assert pedido['ruta'] == RUTA
        assert pedido['encabezados']['X-Internal-Key'] == CLAVE
        assert pedido['encabezados']['Content-Type'] == 'application/json'
        assert pedido['cuerpo'] == {
            'complejo_id': 4, 'categoria': CATEGORIA_AVISO_RESERVAS, 'prioridad': PRIORIDAD_AVISO_URGENTE,
            'mensaje': 'La excepción id 9 deja 2 fechas en espera.',
        }

    def test_un_aviso_personal_viaja_solo_con_el_usuario(self, node):
        AvisoComplejoService.entregar(_aviso(complejo_id=None, usuario_id=31, prioridad=PRIORIDAD_AVISO_NORMAL))

        assert node.pedidos[0]['cuerpo'] == {
            'usuario_id': 31, 'categoria': CATEGORIA_AVISO_RESERVAS, 'prioridad': PRIORIDAD_AVISO_NORMAL,
            'mensaje': 'La excepción id 9 deja 2 fechas en espera.',
        }

    def test_el_evento_viaja_junto_al_aviso(self, node):
        evento = {'tipo_evento': 3, 'usuario_id': 31, 'metadata': {'reserva_id': 20}}

        AvisoComplejoService.entregar(_aviso(evento=evento))

        assert node.pedidos[0]['cuerpo']['evento'] == evento

    @pytest.mark.parametrize('base', ['{url}', '{url}/', '{url}/api', '{url}/api/'])
    def test_acepta_la_url_de_node_con_o_sin_api(self, node, settings, base):
        settings.NODE_API_URL = base.format(url=node.url)

        AvisoComplejoService.entregar(_aviso())

        assert node.pedidos[0]['ruta'] == RUTA

    def test_una_entrega_exitosa_no_deja_nada_en_el_log(self, node, registro_de_avisos):
        AvisoComplejoService.entregar(_aviso())

        assert registro_de_avisos.records == []


class TestFallasDeEntrega:
    """Ninguna falla de Node se propaga: la operación que originó el aviso ya está confirmada."""

    @pytest.mark.parametrize('estado', [400, 401, 429, 500, 502])
    def test_una_respuesta_de_error_queda_en_el_log_con_el_aviso(self, node, registro_de_avisos, estado):
        node.estado = estado

        AvisoComplejoService.entregar(_aviso())

        (registro,) = registro_de_avisos.records
        assert registro.levelname == 'ERROR'
        assert f'HTTP {estado}' in registro.getMessage()
        assert 'complejo 4' in registro.getMessage() and 'deja 2 fechas en espera' in registro.getMessage()

    def test_el_log_de_un_aviso_personal_indica_el_usuario(self, node, registro_de_avisos):
        node.estado = 500

        AvisoComplejoService.entregar(_aviso(complejo_id=None, usuario_id=31))

        assert 'Aviso para el usuario 31 sin entregar' in registro_de_avisos.text

    def test_un_node_caido_queda_en_el_log(self, settings, registro_de_avisos):
        with NodeSimulado() as apagado:
            url = apagado.url
        settings.NODE_API_URL, settings.INTERNAL_API_KEY = url, CLAVE

        AvisoComplejoService.entregar(_aviso())

        assert registro_de_avisos.records[0].levelname == 'ERROR'
        assert 'sin entregar' in registro_de_avisos.text

    def test_no_espera_a_node_mas_que_el_tiempo_maximo(self, node, registro_de_avisos, monkeypatch):
        monkeypatch.setattr(node_client, 'TIEMPO_MAXIMO_SEGUNDOS', 0.2)
        node.demora = 1

        inicio = time.monotonic()
        AvisoComplejoService.entregar(_aviso())

        assert time.monotonic() - inicio < 0.9
        assert 'sin entregar' in registro_de_avisos.text

    def test_no_sigue_redirecciones(self, node, registro_de_avisos):
        node.estado = 302
        node.encabezados_extra = {'Location': 'http://ejemplo.invalid/robar'}

        AvisoComplejoService.entregar(_aviso())

        assert len(node.pedidos) == 1
        assert 'HTTP 302' in registro_de_avisos.text

    def test_una_respuesta_que_no_es_json_queda_en_el_log(self, node, registro_de_avisos):
        node.crudo = b'<html>mantenimiento</html>'

        AvisoComplejoService.entregar(_aviso())

        assert len(node.pedidos) == 1
        assert 'no es JSON' in registro_de_avisos.text

    def test_la_clave_nunca_aparece_en_el_log(self, node, registro_de_avisos):
        node.estado = 401

        AvisoComplejoService.entregar(_aviso())

        assert CLAVE not in registro_de_avisos.text


class TestSinConfiguracion:
    @pytest.mark.parametrize('url, clave', [
        ('', CLAVE),
        ('http://127.0.0.1:9', ''),
        ('http://127.0.0.1:9', 'corta'),
    ])
    def test_sin_url_o_sin_clave_valida_el_aviso_queda_en_el_log_sin_intentar(
        self, settings, registro_de_avisos, monkeypatch, url, clave,
    ):
        settings.NODE_API_URL, settings.INTERNAL_API_KEY = url, clave
        monkeypatch.setattr(node_client, '_enviar', lambda *args: pytest.fail('No debería intentar la entrega.'))

        AvisoComplejoService.entregar(_aviso())

        (registro,) = registro_de_avisos.records
        assert registro.levelname == 'WARNING'
        assert 'sin entregar' in registro.getMessage() and 'prioridad 2' in registro.getMessage()

    @pytest.mark.parametrize('url', ['file:///etc/passwd', 'ftp://node:21', 'node:3000'])
    def test_una_url_que_no_es_http_no_se_usa(self, settings, registro_de_avisos, monkeypatch, url):
        settings.NODE_API_URL, settings.INTERNAL_API_KEY = url, CLAVE
        monkeypatch.setattr(node_client, '_enviar', lambda *args: pytest.fail('No debería intentar la entrega.'))

        AvisoComplejoService.entregar(_aviso())

        assert 'sin entregar' in registro_de_avisos.text

    def test_los_tests_nunca_apuntan_a_un_node_real(self, settings):
        assert settings.NODE_API_URL == '' and settings.INTERNAL_API_KEY == ''


@pytest.mark.django_db
class TestProgramar:
    def test_se_entrega_recien_despues_del_commit(self, node, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks() as pendientes:
            AvisoComplejoService.programar(4, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL, 'Aviso de prueba.')
            assert node.pedidos == []

        for callback in pendientes:
            callback()
        assert node.pedidos[0]['cuerpo']['complejo_id'] == 4

    def test_admite_un_destinatario_usuario_y_un_evento(self, node, django_capture_on_commit_callbacks):
        evento = {'tipo_evento': 3, 'usuario_id': 31, 'metadata': {'reserva_id': 20}}
        with django_capture_on_commit_callbacks(execute=True):
            AvisoComplejoService.programar(
                None, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL, 'Tu reserva id 20 fue cancelada.',
                usuario_id=31,
            )
            AvisoComplejoService.programar(
                4, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL, 'Nueva reserva id 20.', evento=evento,
            )

        personal, del_complejo = (pedido['cuerpo'] for pedido in node.pedidos)
        assert personal['usuario_id'] == 31 and 'complejo_id' not in personal
        assert del_complejo['evento'] == evento

    def test_un_mensaje_largo_se_recorta_al_maximo_de_node(self, node, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            AvisoComplejoService.programar(4, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL, 'a' * 400)

        mensaje = node.pedidos[0]['cuerpo']['mensaje']
        assert len(mensaje) == 280 and mensaje.endswith('…')

    def test_un_aviso_sin_destinatario_es_un_error_de_programacion(self):
        with pytest.raises(ValueError):
            AvisoComplejoService.programar(None, CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL, 'Sin destino.')


def test_lista_de_ids_resume_las_largas():
    from core.services import _lista_de_ids

    assert _lista_de_ids([3, 1, 2]) == '[3, 1, 2]'
    assert _lista_de_ids(list(range(1, 15))) == '[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, …] y 4 más'


class TestDeExtremoAExtremo:
    """La baja de una cuenta con reservas señadas llega a backend-node como avisos reales."""

    def test_la_baja_de_cuenta_entrega_los_avisos_al_complejo(
        self, node, jugador, complejo, cliente_de, con_reservas, django_capture_on_commit_callbacks,
    ):
        respuesta = _baja(cliente_de, jugador, django_capture_on_commit_callbacks)

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        prioridades = sorted(pedido['cuerpo']['prioridad'] for pedido in node.pedidos)
        assert prioridades == [PRIORIDAD_AVISO_NORMAL, PRIORIDAD_AVISO_URGENTE]
        assert all(pedido['cuerpo']['complejo_id'] == complejo.id for pedido in node.pedidos)
        assert all('Lucía' not in pedido['cuerpo']['mensaje'] for pedido in node.pedidos)

    def test_con_node_caido_la_baja_se_confirma_igual(
        self, settings, jugador, cliente_de, con_reservas, registro_de_avisos, django_capture_on_commit_callbacks,
    ):
        with NodeSimulado() as apagado:
            url = apagado.url
        settings.NODE_API_URL, settings.INTERNAL_API_KEY = url, CLAVE

        respuesta = _baja(cliente_de, jugador, django_capture_on_commit_callbacks)

        jugador.refresh_from_db()
        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        assert jugador.estado == 0
        assert registro_de_avisos.text.count('sin entregar') == 2


from core.tests.test_perfil import _baja, con_reservas  # noqa: E402,F401
