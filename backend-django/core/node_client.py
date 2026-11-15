"""
Cliente HTTP de backend-node para las rutas internas: el aviso de notificaciones (POST) y el estado del servicio
(GET). Usa la biblioteca estándar: un único pedido con tiempo máximo, sin redirecciones y autenticado con la clave
compartida entre servicios. La URL y la clave salen de la configuración, nunca del pedido de un usuario.
"""
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from django.conf import settings

RUTA_NOTIFICACIONES = '/api/interno/notificaciones'
RUTA_ESTADO = '/api/interno/estado'
LARGO_MINIMO_DE_CLAVE = 32


class NodeNoConfigurado(Exception):
    """Falta la URL de backend-node o la clave compartida: el entorno no tiene la mensajería conectada."""


class NodeNoDisponible(Exception):
    """backend-node no recibió el aviso: no respondió a tiempo, rechazó el pedido o devolvió algo inesperado."""


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    # Una redirección llevaría la clave a otro destino: se trata como una respuesta de error.
    def redirect_request(self, *args, **kwargs):
        return None


_abridor = urllib.request.build_opener(_SinRedirecciones)


def _url_interna(ruta):
    base = (settings.NODE_API_URL or '').strip().rstrip('/')
    clave = settings.INTERNAL_API_KEY or ''
    partes = urlsplit(base)
    if partes.scheme not in ('http', 'https') or not partes.netloc or len(clave) < LARGO_MINIMO_DE_CLAVE:
        raise NodeNoConfigurado()
    if base.endswith('/api'):
        base = base[:-len('/api')]
    return f'{base}{ruta}', clave


def _pedir(pedido):
    try:
        with _abridor.open(pedido, timeout=settings.NODE_TIMEOUT_SEGUNDOS) as respuesta:
            return json.loads(respuesta.read())
    except urllib.error.HTTPError as error:
        raise NodeNoDisponible(f'respondió HTTP {error.code}') from error
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        raise NodeNoDisponible(f'no respondió ({type(error).__name__})') from error
    except ValueError as error:
        raise NodeNoDisponible('devolvió una respuesta que no es JSON') from error


def _enviar(url, clave, datos):
    return _pedir(urllib.request.Request(
        url,
        data=json.dumps(datos).encode('utf-8'),
        method='POST',
        headers={'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Internal-Key': clave},
    ))


def _consultar(url, clave):
    return _pedir(urllib.request.Request(
        url, method='GET', headers={'Accept': 'application/json', 'X-Internal-Key': clave},
    ))


def enviar_notificacion(datos):
    """Entrega un aviso a backend-node y devuelve su respuesta (`{id, ids, evento, omitidas}`)."""
    url, clave = _url_interna(RUTA_NOTIFICACIONES)
    return _enviar(url, clave, datos)


def consultar_estado():
    """Estado de backend-node (memoria, latencia de MongoDB, actividad y fallas recientes) para el reporte de sistema."""
    url, clave = _url_interna(RUTA_ESTADO)
    return _consultar(url, clave)
