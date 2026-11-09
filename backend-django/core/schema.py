import graphene
from django.http import HttpRequest, QueryDict
from graphql import GraphQLError

from .views import ComplejoViewSet, ReservaViewSet


def listar_como_en_rest(clase_vista, accion, info, argumentos):
    """
    Ejecuta la acción de listado de un ViewSet de la API REST, con los argumentos de GraphQL como parámetros de
    consulta, a través de su propio `as_view`: misma autenticación, permisos RBAC, limitadores, filtros, orden,
    paginación, serializer y manejo de errores, incluida la auditoría de los 403. Las dos APIs no pueden divergir
    en qué muestran ni a quién.
    """
    consulta = QueryDict(mutable=True)
    for clave, valor in argumentos.items():
        if valor is not None:
            consulta.setlist(clave, [str(item) for item in valor] if isinstance(valor, list) else [str(valor)])
    peticion = HttpRequest()
    peticion.method = 'GET'
    peticion.GET = consulta
    # Solo los encabezados: el token sale de Authorization y nunca de una cookie de sesión.
    peticion.META = info.context.META

    respuesta = clase_vista.as_view({'get': accion})(peticion)
    if respuesta.status_code >= 400:
        detalle = respuesta.data['detail']
        raise GraphQLError(
            detalle if isinstance(detalle, str) else 'Datos inválidos.',
            extensions={'codigo': respuesta.status_code, 'detalle': detalle},
        )
    return {'count': respuesta.data['count'], 'results': respuesta.data['results']}


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


class ReservaPropiaType(graphene.ObjectType):
    id = graphene.Int(required=True)
    complejo = graphene.Field(ReferenciaType, required=True)
    cancha = graphene.Field(ReferenciaType, required=True)
    deporte = graphene.String(required=True)
    fecha_turno = graphene.String(required=True, description='AAAA-MM-DD')
    hora_inicio = graphene.String(required=True, description='HH:MM:SS')
    hora_fin = graphene.String(required=True, description='HH:MM:SS')
    precio_acordado = graphene.Decimal(required=True)
    tipo_ocupacion = graphene.Int(required=True)
    tipo_ocupacion_nombre = graphene.String(required=True)
    estado = graphene.Int(required=True)
    estado_nombre = graphene.String(required=True)
    cancelable_hasta = graphene.String(description='Fecha y hora ISO 8601 con zona horaria')
    fecha_creacion = graphene.String(required=True, description='Fecha y hora ISO 8601 con zona horaria')


class PaginaReservasType(graphene.ObjectType):
    count = graphene.Int(required=True)
    results = graphene.List(graphene.NonNull(ReservaPropiaType), required=True)


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

    mis_reservas = graphene.Field(
        PaginaReservasType,
        estado=graphene.Int(),
        vigencia=graphene.String(),
        fecha_desde=graphene.String(),
        fecha_hasta=graphene.String(),
        ordering=graphene.String(),
        page=graphene.Int(),
        description='Reservas de la cuenta autenticada, con los filtros y la paginación de la API REST.',
    )

    @staticmethod
    def resolve_catalogo_complejos(root, info, **argumentos):
        return listar_como_en_rest(ComplejoViewSet, 'list', info, argumentos)

    @staticmethod
    def resolve_mis_reservas(root, info, **argumentos):
        return listar_como_en_rest(ReservaViewSet, 'mias', info, argumentos)


schema = graphene.Schema(query=Query)
