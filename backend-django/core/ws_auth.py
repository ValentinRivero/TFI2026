"""
Identificación opcional para el WebSocket de disponibilidad. La grilla es pública: un token ausente, vencido
o inválido no cierra la conexión, solo deja al cliente como anónimo en modo lectura.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import AccessToken

from .repositories import UsuarioRepository


def _token_de_la_query(scope):
    parametros = parse_qs(scope.get('query_string', b'').decode('latin-1'))
    valores = parametros.get('token')
    return valores[0] if valores else None


@database_sync_to_async
def _usuario_activo(usuario_id):
    return UsuarioRepository.obtener_activo_por_id(usuario_id)


async def usuario_del_token(token):
    """Usuario activo dueño de un access válido, o AnonymousUser ante cualquier problema con el token."""
    if not token:
        return AnonymousUser()
    try:
        # SimpleJWT emite usuario_id como texto: se convierte a entero antes de consultar.
        usuario_id = int(AccessToken(token)[jwt_settings.USER_ID_CLAIM])
    except (TokenError, KeyError, TypeError, ValueError):
        return AnonymousUser()
    return await _usuario_activo(usuario_id) or AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Lee `?token=<access>` y deja en `scope['user']` al usuario identificado o a AnonymousUser."""

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope['user'] = await usuario_del_token(_token_de_la_query(scope))
        return await super().__call__(scope, receive, send)
