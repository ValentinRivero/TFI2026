"""
Listas blancas de parámetros de consulta. Solo los filtros declarados se aplican; un valor inválido
responde 400 y nunca llega al ORM como texto libre.
"""
import unicodedata

import django_filters
from django.db.models import CharField, TextField, Transform
from django.utils import timezone
from rest_framework.filters import SearchFilter

from .models import (
    Cobertura,
    DiaSemana,
    EstadoCancha,
    EstadoContrato,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    TipoMotivoExcepcion,
    TipoOcupacion,
)
from .repositories import (
    CatalogoRepository,
    ComplejoRepository,
    ExcepcionHorariaRepository,
    ReservaRepository,
    RolRepository,
    TurnoFijoRepository,
)


def quitar_acentos(texto):
    if texto is None:
        return None
    descompuesto = unicodedata.normalize('NFD', str(texto))
    return ''.join(caracter for caracter in descompuesto if unicodedata.category(caracter) != 'Mn').lower()


@CharField.register_lookup
@TextField.register_lookup
class SinAcentos(Transform):
    """
    Compara sin tildes: en PostgreSQL usa la extensión unaccent (migración 0006) y en SQLite una función
    equivalente registrada al abrir la conexión, así las pruebas ejercitan la misma consulta.
    """

    lookup_name = 'sin_acentos'
    function = 'SIN_ACENTOS'

    def as_postgresql(self, compiler, connection, **extra):
        return super().as_sql(compiler, connection, function='UNACCENT', **extra)


def registrar_sin_acentos_en_sqlite(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        connection.connection.create_function('SIN_ACENTOS', 1, quitar_acentos, deterministic=True)


class BusquedaFlexibleFilter(SearchFilter):
    """`?search=` ignora mayúsculas y tildes en ambos lados: «timbos» encuentra «Los Timbós» y viceversa."""

    def get_search_terms(self, request):
        return [quitar_acentos(termino) for termino in super().get_search_terms(request)]

    def construct_search(self, field_name, queryset):
        return f'{field_name}__sin_acentos__icontains'

ESTADOS_CANCHA_VISIBLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoCancha.choices if valor != EstadoCancha.BAJA
]


class CatalogoComplejoFilter(django_filters.FilterSet):
    deporte = django_filters.ModelChoiceFilter(queryset=CatalogoRepository.deportes_activos())
    cobertura = django_filters.TypedChoiceFilter(choices=Cobertura.choices, coerce=int)
    servicio = django_filters.ModelMultipleChoiceFilter(queryset=CatalogoRepository.servicios_activos())

    def filter_queryset(self, queryset):
        # deporte y cobertura se exigen sobre una misma cancha activa: "pádel techado" no lo cumple
        # un complejo con pádel descubierto y una cancha de fútbol techada.
        datos = self.form.cleaned_data
        condiciones_cancha = {}
        if datos.get('deporte') is not None:
            condiciones_cancha['deporte'] = datos['deporte']
        if datos.get('cobertura') not in (None, ''):
            condiciones_cancha['cobertura'] = datos['cobertura']
        if condiciones_cancha:
            queryset = ComplejoRepository.filtrar_por_canchas(queryset, **condiciones_cancha)
        if datos.get('servicio'):
            queryset = ComplejoRepository.filtrar_por_servicios(queryset, [servicio.pk for servicio in datos['servicio']])
        return queryset


class ContratoFilter(django_filters.FilterSet):
    estado_contrato = django_filters.TypedChoiceFilter(choices=EstadoContrato.choices, coerce=int)
    propietario = django_filters.NumberFilter(field_name='propietario_id')
    # Permite listar, por ejemplo, contratos activos cuyo titular está suspendido.
    estado_propietario = django_filters.TypedChoiceFilter(
        field_name='propietario__estado', choices=EstadoUsuario.choices, coerce=int,
    )


class UsuarioFilter(django_filters.FilterSet):
    estado = django_filters.TypedChoiceFilter(choices=EstadoUsuario.choices, coerce=int)
    rol = django_filters.ModelChoiceFilter(field_name='rol', to_field_name='nombre', queryset=RolRepository.activos())


class CanchaFilter(django_filters.FilterSet):
    complejo = django_filters.NumberFilter(field_name='complejo_id')
    deporte = django_filters.NumberFilter(field_name='deporte_id')
    estado = django_filters.TypedChoiceFilter(choices=ESTADOS_CANCHA_VISIBLES, coerce=int)


class HorarioAperturaFilter(django_filters.FilterSet):
    cancha = django_filters.NumberFilter(field_name='cancha_id')
    dia_semana = django_filters.TypedChoiceFilter(choices=DiaSemana.choices, coerce=int)


VIGENCIA_EXCEPCION = (('vigentes', 'Vigentes'), ('finalizadas', 'Finalizadas'))


class ExcepcionHorariaFilter(django_filters.FilterSet):
    complejo = django_filters.NumberFilter(field_name='complejo_id')
    # Una cancha también queda cerrada por las excepciones globales de su complejo: se listan ambas.
    cancha = django_filters.NumberFilter(method='filtrar_cancha')
    vigencia = django_filters.ChoiceFilter(choices=VIGENCIA_EXCEPCION, method='filtrar_vigencia')
    fecha = django_filters.DateFilter(method='filtrar_fecha', input_formats=['%Y-%m-%d'])
    tipo_motivo = django_filters.TypedChoiceFilter(choices=TipoMotivoExcepcion.choices, coerce=int)

    def filtrar_cancha(self, queryset, nombre, valor):
        return ExcepcionHorariaRepository.que_afectan_a_cancha(queryset, valor)

    def filtrar_vigencia(self, queryset, nombre, valor):
        hoy = timezone.localdate()
        if valor == 'vigentes':
            return queryset.filter(fecha_fin__gte=hoy)
        return queryset.filter(fecha_fin__lt=hoy)

    def filtrar_fecha(self, queryset, nombre, valor):
        return ExcepcionHorariaRepository.que_cubren_fecha(queryset, valor)


FORMATO_FECHA_ISO = ['%Y-%m-%d']

ESTADOS_RESERVA_VISIBLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoReserva.choices if valor != EstadoReserva.BAJA
]
VIGENCIA_RESERVA = (('proximas', 'Próximas'), ('pasadas', 'Pasadas'))


class RangoDeFechasDeTurnoFilter(django_filters.FilterSet):
    estado = django_filters.TypedChoiceFilter(choices=ESTADOS_RESERVA_VISIBLES, coerce=int)
    fecha_desde = django_filters.DateFilter(field_name='fecha_turno', lookup_expr='gte', input_formats=FORMATO_FECHA_ISO)
    fecha_hasta = django_filters.DateFilter(field_name='fecha_turno', lookup_expr='lte', input_formats=FORMATO_FECHA_ISO)


class ReservaPropiaFilter(RangoDeFechasDeTurnoFilter):
    vigencia = django_filters.ChoiceFilter(choices=VIGENCIA_RESERVA, method='filtrar_vigencia')

    def filtrar_vigencia(self, queryset, nombre, valor):
        ahora = timezone.localtime()
        return ReservaRepository.filtrar_por_vigencia(queryset, valor == 'proximas', ahora.date(), ahora.time())


class AgendaFilter(RangoDeFechasDeTurnoFilter):
    complejo = django_filters.NumberFilter(field_name='cancha__complejo_id')
    cancha = django_filters.NumberFilter(field_name='cancha_id')
    fecha = django_filters.DateFilter(field_name='fecha_turno', input_formats=FORMATO_FECHA_ISO)
    tipo_ocupacion = django_filters.TypedChoiceFilter(choices=TipoOcupacion.choices, coerce=int)


ESTADOS_TURNO_FIJO_VISIBLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoTurnoFijo.choices if valor != EstadoTurnoFijo.BAJA
]


class TurnoFijoFilter(django_filters.FilterSet):
    complejo = django_filters.NumberFilter(field_name='cancha__complejo_id')
    cancha = django_filters.NumberFilter(field_name='cancha_id')
    dia_semana = django_filters.TypedChoiceFilter(choices=DiaSemana.choices, coerce=int)
    estado = django_filters.TypedChoiceFilter(choices=ESTADOS_TURNO_FIJO_VISIBLES, coerce=int)
    # Turnos fijos que caen en esa fecha: la agenda del día los combina con las reservas.
    fecha = django_filters.DateFilter(method='filtrar_fecha', input_formats=FORMATO_FECHA_ISO)

    def filtrar_fecha(self, queryset, nombre, valor):
        return TurnoFijoRepository.que_aplican_en(queryset, valor)
