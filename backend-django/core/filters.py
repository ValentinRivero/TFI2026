"""
Listas blancas de parámetros de consulta. Solo los filtros declarados se aplican; un valor inválido
responde 400 y nunca llega al ORM como texto libre.
"""
import unicodedata

import django_filters
from django.db.models import CharField, TextField, Transform
from rest_framework.filters import SearchFilter

from .models import Cobertura, DiaSemana, EstadoCancha, EstadoContrato, EstadoUsuario
from .repositories import CatalogoRepository, ComplejoRepository, RolRepository


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
