import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from graphene_django.views import GraphQLView, HttpError
from graphql import GraphQLError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

MENSAJE_ERROR_INTERNO = 'Error interno del servidor.'
MENSAJES_DE_TRANSPORTE = {
    400: 'La solicitud debe enviar una consulta GraphQL en un JSON válido.',
    405: 'GraphQL se consulta con POST.',
}


class JWTGraphQLView(GraphQLView):
    """
    GraphQL sobre el mismo JWT que la API REST. El usuario sale solo del encabezado Authorization: nunca de la
    sesión de Django, para que una cookie no autentique sin CSRF. Como las rutas públicas de REST, un token
    inválido o vencido no corta la consulta: el usuario queda anónimo y cada campo aplica sus propios permisos.
    """

    def dispatch(self, request, *args, **kwargs):
        request.user = self._usuario_del_token(request)
        # Fuera de desarrollo GET no ejecuta consultas: los parámetros de una URL quedan en logs e historiales.
        if request.method != 'POST' and not (request.method == 'GET' and self.can_display_graphiql(request, {})):
            respuesta = JsonResponse({'errors': [{'message': MENSAJES_DE_TRANSPORTE[405]}]}, status=405)
            respuesta['Allow'] = 'POST'
            return respuesta
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _usuario_del_token(request):
        try:
            identificacion = JWTAuthentication().authenticate(request)
        except AuthenticationFailed:
            return AnonymousUser()
        return identificacion[0] if identificacion else AnonymousUser()

    def can_display_graphiql(self, request, data):
        return settings.DEBUG and super().can_display_graphiql(request, data)

    @staticmethod
    def format_error(error):
        if isinstance(error, HttpError):
            return {'message': MENSAJES_DE_TRANSPORTE.get(error.response.status_code, MENSAJE_ERROR_INTERNO)}
        original = getattr(error, 'original_error', None)
        if original is not None and not isinstance(original, GraphQLError):
            # El detalle de una excepción no prevista (rutas, hosts, SQL) queda en el log y no en la respuesta.
            logger.error('Error no controlado en GraphQL', exc_info=original)
            return {**GraphQLView.format_error(error), 'message': MENSAJE_ERROR_INTERNO}
        return GraphQLView.format_error(error)

