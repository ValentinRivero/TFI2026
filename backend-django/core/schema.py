from functools import wraps

import graphene
from django.http import HttpRequest, QueryDict
from graphql import GraphQLError
from rest_framework.exceptions import APIException, ValidationError

from .views import ComplejoViewSet


def _error_de_api(error):
    mensaje = 'Datos inválidos.' if isinstance(error, ValidationError) else str(error.detail)
    return GraphQLError(mensaje, extensions={'codigo': error.status_code, 'detalle': error.detail})


def con_errores_de_api(resolver):
    """Las excepciones de DRF (400, 401, 403, 404, 429) llegan al cliente con su código en `extensions`."""

    @wraps(resolver)
    def _resolver(*args, **kwargs):
        try:
            return resolver(*args, **kwargs)
        except APIException as error:
            raise _error_de_api(error) from error

    return _resolver


def listar_como_en_rest(clase_vista, info, argumentos):
    """
    Ejecuta la acción `list` del ViewSet de la API REST con los argumentos de GraphQL como parámetros de consulta.
    Pasa por la misma autenticación, permisos, limitadores, filtros, búsqueda, orden, paginación y serializer, así
    las dos APIs no pueden divergir en qué muestran ni a quién.
    """
    consulta = QueryDict(mutable=True)
    for clave, valor in argumentos.items():
        if valor is not None:
            consulta.setlist(clave, [str(item) for item in valor] if isinstance(valor, list) else [str(valor)])
    peticion = HttpRequest()
    peticion.method = 'GET'
    peticion.GET = consulta
    peticion.META = info.context.META

    vista = clase_vista(action_map={'get': 'list'}, args=(), kwargs={}, format_kwarg=None)
    vista.request = vista.initialize_request(peticion)
    vista.initial(vista.request)
    pagina = vista.paginate_queryset(vista.filter_queryset(vista.get_queryset()))
    return {'count': vista.paginator.page.paginator.count, 'results': vista.get_serializer(pagina, many=True).data}


class ReferenciaType(graphene.ObjectType):
    id = graphene.Int(required=True)
    nombre = graphene.String(required=True)


class ComplejoCatalogoType(graphene.ObjectType):
    id = graphene.Int(required=True)
    nombre = graphene.String(required=True)
    direccion = graphene.String()
    latitud = graphene.Decimal()
    longitud = graphene.Decimal()
    telefono_contacto = graphene.String()
    horas_limite_cancelacion = graphene.Int()
    info_sena = graphene.String()
    precio_desde = graphene.Decimal()
    servicios = graphene.List(graphene.NonNull(ReferenciaType), required=True)
    deportes = graphene.List(graphene.NonNull(ReferenciaType), required=True)


class PaginaCatalogoType(graphene.ObjectType):
    count = graphene.Int(required=True)
    results = graphene.List(graphene.NonNull(ComplejoCatalogoType), required=True)


class Query(graphene.ObjectType):
    catalogo_complejos = graphene.Field(
        PaginaCatalogoType,
        deporte=graphene.Int(),
        cobertura=graphene.Int(),
        servicio=graphene.List(graphene.Int),
        search=graphene.String(),
        ordering=graphene.String(),
        page=graphene.Int(),
        description='Complejos habilitados del catálogo público, con los filtros y la paginación de la API REST.',
    )

    @staticmethod
    @con_errores_de_api
    def resolve_catalogo_complejos(root, info, **argumentos):
        return listar_como_en_rest(ComplejoViewSet, info, argumentos)


schema = graphene.Schema(query=Query)
