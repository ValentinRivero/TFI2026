import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from graphene.utils.is_introspection_key import is_introspection_key
from graphene.validation import DisableIntrospection, depth_limit_validator
from graphene_django.views import GraphQLView, HttpError
from graphql import GraphQLError
from graphql.language import FieldNode, FragmentSpreadNode, InlineFragmentNode
from graphql.validation import ValidationRule, specified_rules
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework_simplejwt.authentication import JWTAuthentication

from .exceptions import custom_exception_handler
from .throttles import GraphQLRateThrottle

logger = logging.getLogger(__name__)

MENSAJE_ERROR_INTERNO = 'Error interno del servidor.'
MENSAJES_DE_TRANSPORTE = {
    400: 'La solicitud debe enviar una consulta GraphQL en un JSON válido.',
    405: 'GraphQL se consulta con POST.',
}
# El esquema no tiene ciclos y su consulta más profunda llega a 3 niveles: el margen cubre tipos futuros con
# relaciones sin habilitar consultas recursivas.
MAXIMO_PROFUNDIDAD_GRAPHQL = 5
MAXIMO_CAMPOS_RAIZ_GRAPHQL = 5
MENSAJE_DEMASIADOS_CAMPOS = f'Una operación admite como máximo {MAXIMO_CAMPOS_RAIZ_GRAPHQL} campos de primer nivel.'


class LimiteDeCamposRaiz(ValidationRule):
    """
    Cada campo de primer nivel ejecuta una vista completa de la API REST: con alias, una sola petición podría pedir
    cien veces el catálogo o encadenar altas de reservas. Se cuentan también los que llegan por fragmentos.
    """

    def enter_operation_definition(self, node, *_args):
        if self._contar(node.selection_set, set()) > MAXIMO_CAMPOS_RAIZ_GRAPHQL:
            self.report_error(GraphQLError(MENSAJE_DEMASIADOS_CAMPOS, node))

    def _contar(self, seleccion, fragmentos_vistos):
        total = 0
        for elemento in seleccion.selections:
            if isinstance(elemento, FieldNode):
                total += 0 if is_introspection_key(elemento.name.value) else 1
            elif isinstance(elemento, InlineFragmentNode):
                total += self._contar(elemento.selection_set, fragmentos_vistos)
            elif isinstance(elemento, FragmentSpreadNode) and elemento.name.value not in fragmentos_vistos:
                fragmentos_vistos.add(elemento.name.value)
                fragmento = self.context.get_fragment(elemento.name.value)
                if fragmento is not None:
                    total += self._contar(fragmento.selection_set, fragmentos_vistos)
        return total


def reglas_de_validacion():
    # Las reglas propias se suman a las estándar de GraphQL: pasarlas solas reemplazaría la validación del esquema.
    reglas = [*specified_rules, depth_limit_validator(max_depth=MAXIMO_PROFUNDIDAD_GRAPHQL), LimiteDeCamposRaiz]
    if not settings.DEBUG:
        reglas.append(DisableIntrospection)
    return reglas


class JWTGraphQLView(GraphQLView):
    """
    GraphQL sobre el mismo JWT que la API REST. El usuario sale solo del encabezado Authorization: nunca de la
    sesión de Django, para que una cookie no autentique sin CSRF. Como las rutas públicas de REST, un token
    inválido o vencido no corta la consulta: el usuario queda anónimo y cada campo aplica sus propios permisos.
    """

    def dispatch(self, request, *args, **kwargs):
        request.user = self._usuario_del_token(request)
        limitador = GraphQLRateThrottle()
        if not limitador.allow_request(request, self):
            return self._limite_superado(request, limitador.wait())
        # Fuera de desarrollo GET no ejecuta consultas: los parámetros de una URL quedan en logs e historiales.
        if request.method != 'POST' and not (request.method == 'GET' and self.can_display_graphiql(request, {})):
            respuesta = JsonResponse({'errors': [{'message': MENSAJES_DE_TRANSPORTE[405]}]}, status=405)
            respuesta['Allow'] = 'POST'
            return respuesta
        self.validation_rules = reglas_de_validacion()
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _usuario_del_token(request):
        try:
            identificacion = JWTAuthentication().authenticate(request)
        except AuthenticationFailed:
            return AnonymousUser()
        return identificacion[0] if identificacion else AnonymousUser()

    @staticmethod
    def _limite_superado(request, espera):
        """El mensaje, el encabezado Retry-After y la auditoría del 429 salen del manejador de errores de REST."""
        error = custom_exception_handler(Throttled(wait=espera), {'request': request})
        respuesta = JsonResponse({'errors': [{'message': error.data['detail']}]}, status=error.status_code)
        if 'Retry-After' in error:
            respuesta['Retry-After'] = error['Retry-After']
        return respuesta

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
