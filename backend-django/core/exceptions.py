import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback
from rest_framework_simplejwt.exceptions import InvalidToken

logger = logging.getLogger('django.request')


class ConflictoNegocio(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La operación entra en conflicto con el estado actual del recurso.'
    default_code = 'conflicto'


class ServicioNoDisponible(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'El servicio no está disponible en este momento.'
    default_code = 'servicio_no_disponible'


MENSAJES_POR_DEFECTO = {
    exceptions.NotAuthenticated: 'Debés iniciar sesión para acceder a este recurso.',
    exceptions.AuthenticationFailed: 'Las credenciales de autenticación no son válidas.',
    exceptions.PermissionDenied: 'No tenés permiso para realizar esta acción.',
    exceptions.NotFound: 'No se encontró el recurso solicitado.',
    exceptions.ParseError: 'El cuerpo de la solicitud tiene un formato inválido.',
    exceptions.UnsupportedMediaType: 'El tipo de contenido de la solicitud no está soportado.',
    exceptions.NotAcceptable: 'No se puede responder en el formato solicitado.',
}

# Códigos que SimpleJWT emite en inglés al autenticar con un access token.
MENSAJES_POR_CODIGO = {
    'user_inactive': 'La cuenta no está activa.',
    'user_not_found': 'La cuenta no está activa.',
    'no_active_account': 'La cuenta no está activa.',
    'bad_authorization_header': 'El encabezado Authorization tiene un formato inválido.',
    'password_changed': 'La sesión ya no es válida. Iniciá sesión nuevamente.',
}


def _codigo(exc):
    # SimpleJWT envía algunos rechazos con el detalle como {'detail': ..., 'code': ...}.
    if isinstance(exc.detail, dict) and 'code' in exc.detail:
        return str(exc.detail['code'])
    if isinstance(exc.detail, str):
        return exc.get_codes()
    return None


def _mensaje_en_espanol(exc):
    if isinstance(exc, InvalidToken):
        return 'El token es inválido o expiró.'
    if isinstance(exc, exceptions.Throttled):
        if exc.wait:
            return f'Superaste el límite de solicitudes. Intentá nuevamente en {int(exc.wait) or 1} segundos.'
        return 'Superaste el límite de solicitudes. Intentá nuevamente más tarde.'
    if isinstance(exc, exceptions.MethodNotAllowed):
        return 'El método de la solicitud no está permitido en este recurso.'

    codigo = _codigo(exc)
    if codigo in MENSAJES_POR_CODIGO:
        return MENSAJES_POR_CODIGO[codigo]

    # Solo se reemplaza el texto genérico de la librería: los mensajes propios ya vienen en español.
    for clase, mensaje in MENSAJES_POR_DEFECTO.items():
        if type(exc) is clase and str(exc.detail) == str(clase.default_detail):
            return mensaje
    return None


def _detalle(datos):
    if isinstance(datos, dict) and set(datos) == {'detail'}:
        return datos['detail']
    if isinstance(datos, list) and len(datos) == 1:
        return datos[0]
    return datos


def _convertir_excepcion_django(exc):
    if isinstance(exc, Http404):
        return exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        return exceptions.PermissionDenied()
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'error_dict'):
            return exceptions.ValidationError(exc.message_dict)
        return exceptions.ValidationError(exc.messages)
    return exc


def _auditar(respuesta, context):
    from .services import AuditoriaService

    request = context.get('request')
    if request is None:
        return
    detalle = str(respuesta.data['detail'])
    if respuesta.status_code == status.HTTP_403_FORBIDDEN:
        AuditoriaService.registrar_acceso_denegado(request, detalle)
    elif respuesta.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        AuditoriaService.registrar_limite_peticiones(request, detalle)


def custom_exception_handler(exc, context):
    exc = _convertir_excepcion_django(exc)
    respuesta = exception_handler(exc, context)

    if respuesta is None:
        if settings.DEBUG:
            return None
        logger.error('Error no controlado en la API', exc_info=exc)
        # Al devolver una respuesta se evita la propagación: hay que revertir explícitamente lo escrito en la petición.
        set_rollback()
        return Response(
            {'error': True, 'detail': 'Error interno del servidor.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    mensaje = _mensaje_en_espanol(exc)
    respuesta.data = {
        'error': True,
        'detail': mensaje if mensaje is not None else _detalle(respuesta.data),
    }

    if respuesta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS):
        _auditar(respuesta, context)

    return respuesta
