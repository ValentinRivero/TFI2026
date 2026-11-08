import html
import re
from decimal import Decimal

import nh3
from rest_framework import serializers

from .models import (
    Cancha,
    Complejo,
    EstadoCancha,
    EstadoContrato,
    EstadoUsuario,
    HorarioApertura,
    LogAuditoria,
    TipoEventoAuditoria,
    Usuario,
)
from .repositories import CanchaRepository, CatalogoRepository, ComplejoRepository, RolRepository, UsuarioRepository

MAXIMO_PASADAS_SANITIZACION = 5

PATRON_TELEFONO = re.compile(r'^\+?[0-9\s()-]{6,30}$')
MENSAJE_TELEFONO = 'Ingresá un teléfono válido: solo números, espacios, guiones, paréntesis y un + inicial.'
MENSAJE_SIN_CAMPOS = 'Indicá al menos uno de los campos editables.'


def limpiar_texto(valor):
    """
    Devuelve texto plano sin etiquetas HTML.
    nh3 escapa `&` como `&amp;`; se desescapa y se vuelve a limpiar hasta que el resultado no cambie,
    así "Pérez & Hijos" se guarda tal cual y una etiqueta codificada (`&lt;script&gt;`) no reaparece como HTML.
    """
    if valor is None:
        return valor
    texto = str(valor)
    for _ in range(MAXIMO_PASADAS_SANITIZACION):
        limpio = html.unescape(nh3.clean(texto, tags=set()))
        if limpio == texto:
            return limpio.strip()
        texto = limpio
    return nh3.clean(texto, tags=set()).strip()


def validar_telefono(valor):
    if valor and not PATRON_TELEFONO.match(valor):
        raise serializers.ValidationError(MENSAJE_TELEFONO)
    return valor


class TextoLimpioField(serializers.CharField):
    def to_internal_value(self, data):
        valor = limpiar_texto(super().to_internal_value(data))
        if valor == '' and not self.allow_blank:
            self.fail('blank')
        return valor


class TelefonoField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_telefono(super().to_internal_value(data))


def _exigir_algun_campo(attrs):
    if not attrs:
        raise serializers.ValidationError(MENSAJE_SIN_CAMPOS)
    return attrs


def _latitud(**opciones):
    return serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal('-90'), max_value=Decimal('90'), **opciones,
    )


def _longitud(**opciones):
    return serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal('-180'), max_value=Decimal('180'), **opciones,
    )


def _precio(**opciones):
    return serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'), **opciones)


class LogAuditoriaSerializer(serializers.ModelSerializer):
    fecha_accion = serializers.DateTimeField(source='fecha_creacion', read_only=True)
    tipo_evento_nombre = serializers.CharField(source='get_tipo_evento_display', read_only=True)
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True, default=None)
    complejo_nombre = serializers.CharField(source='complejo.nombre', read_only=True, default=None)

    class Meta:
        model = LogAuditoria
        fields = (
            'id',
            'fecha_accion',
            'tipo_evento',
            'tipo_evento_nombre',
            'accion',
            'detalle',
            'usuario',
            'usuario_email',
            'complejo',
            'complejo_nombre',
            'ip_origen',
        )
        read_only_fields = fields


class FiltroAuditoriaSerializer(serializers.Serializer):
    tipo_evento = serializers.ChoiceField(choices=TipoEventoAuditoria.choices, required=False)
    usuario = serializers.IntegerField(min_value=1, required=False)
    complejo = serializers.IntegerField(min_value=1, required=False)
    ip_origen = serializers.IPAddressField(required=False)
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)

    def validate(self, attrs):
        desde, hasta = attrs.get('fecha_desde'), attrs.get('fecha_hasta')
        if desde and hasta and desde > hasta:
            raise serializers.ValidationError({'fecha_hasta': 'Debe ser igual o posterior a fecha_desde.'})
        return attrs


class CatalogoMaestroSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)


class CanchaPublicaSerializer(serializers.ModelSerializer):
    deporte = CatalogoMaestroSerializer(read_only=True)
    tipo_superficie_nombre = serializers.CharField(source='get_tipo_superficie_display', read_only=True)
    cobertura_nombre = serializers.CharField(source='get_cobertura_display', read_only=True)
    iluminacion_nombre = serializers.CharField(source='get_iluminacion_display', read_only=True)

    class Meta:
        model = Cancha
        fields = (
            'id',
            'nombre',
            'deporte',
            'tipo_superficie',
            'tipo_superficie_nombre',
            'cobertura',
            'cobertura_nombre',
            'iluminacion',
            'iluminacion_nombre',
            'duracion_turno_min',
            'precio_base',
        )
        read_only_fields = fields


def _servicios_activos(complejo):
    return [
        {'id': asignacion.servicio_id, 'nombre': asignacion.servicio.nombre}
        for asignacion in complejo.servicios_activos
    ]


class ComplejoCatalogoSerializer(serializers.ModelSerializer):
    """Datos públicos y comerciales del complejo: no incluye al propietario ni ningún dato personal."""

    precio_desde = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    servicios = serializers.SerializerMethodField()
    deportes = serializers.SerializerMethodField()

    class Meta:
        model = Complejo
        fields = (
            'id',
            'nombre',
            'direccion',
            'latitud',
            'longitud',
            'telefono_contacto',
            'horas_limite_cancelacion',
            'info_sena',
            'precio_desde',
            'servicios',
            'deportes',
        )
        read_only_fields = fields

    def get_servicios(self, complejo):
        return _servicios_activos(complejo)

    def get_deportes(self, complejo):
        deportes = {cancha.deporte_id: cancha.deporte.nombre for cancha in complejo.canchas_activas}
        return [
            {'id': deporte_id, 'nombre': nombre}
            for deporte_id, nombre in sorted(deportes.items(), key=lambda par: (par[1], par[0]))
        ]


class ComplejoDetallePublicoSerializer(ComplejoCatalogoSerializer):
    canchas = serializers.SerializerMethodField()

    class Meta(ComplejoCatalogoSerializer.Meta):
        fields = (*ComplejoCatalogoSerializer.Meta.fields, 'canchas')
        read_only_fields = fields

    def get_canchas(self, complejo):
        return CanchaPublicaSerializer(complejo.canchas_activas, many=True).data


class ComplejoAdminSerializer(serializers.ModelSerializer):
    estado_contrato_nombre = serializers.CharField(source='get_estado_contrato_display', read_only=True)
    servicios = serializers.SerializerMethodField()

    class Meta:
        model = Complejo
        fields = (
            'id',
            'nombre',
            'direccion',
            'latitud',
            'longitud',
            'telefono_contacto',
            'horas_limite_cancelacion',
            'info_sena',
            'estado_contrato',
            'estado_contrato_nombre',
            'propietario',
            'servicios',
            'fecha_modificacion',
        )
        read_only_fields = fields

    def get_servicios(self, complejo):
        return _servicios_activos(complejo)


class ComplejoConfiguracionSerializer(serializers.Serializer):
    nombre = TextoLimpioField(max_length=120, required=False)
    direccion = TextoLimpioField(max_length=160, required=False)
    latitud = _latitud(required=False)
    longitud = _longitud(required=False)
    telefono_contacto = TelefonoField(max_length=30, required=False, allow_blank=True)
    horas_limite_cancelacion = serializers.IntegerField(min_value=0, max_value=168, required=False)
    info_sena = TextoLimpioField(max_length=200, required=False, allow_blank=True)

    def validate(self, attrs):
        return _exigir_algun_campo(attrs)


class ServiciosComplejoSerializer(serializers.Serializer):
    servicios = serializers.PrimaryKeyRelatedField(
        queryset=CatalogoRepository.servicios_activos(), many=True, allow_empty=True,
    )


class PropietarioResumenSerializer(serializers.ModelSerializer):
    """El estado de la cuenta deja a la vista un contrato vigente cuyo titular está suspendido o dado de baja."""

    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Usuario
        fields = ('id', 'nombre_completo', 'email', 'estado', 'estado_nombre')
        read_only_fields = fields


class ContratoSerializer(serializers.ModelSerializer):
    estado_contrato_nombre = serializers.CharField(source='get_estado_contrato_display', read_only=True)
    propietario = PropietarioResumenSerializer(read_only=True)

    class Meta:
        model = Complejo
        fields = (
            'id',
            'nombre',
            'direccion',
            'latitud',
            'longitud',
            'telefono_contacto',
            'horas_limite_cancelacion',
            'info_sena',
            'estado_contrato',
            'estado_contrato_nombre',
            'propietario',
            'fecha_creacion',
            'fecha_modificacion',
        )
        read_only_fields = fields


ESTADOS_CONTRATO_INICIALES = [
    (valor, etiqueta) for valor, etiqueta in EstadoContrato.choices
    if valor in (EstadoContrato.PENDIENTE, EstadoContrato.ACTIVO)
]


class ContratoAltaSerializer(serializers.Serializer):
    propietario = serializers.PrimaryKeyRelatedField(
        queryset=UsuarioRepository.duenos_activos(),
        error_messages={'does_not_exist': 'El propietario debe ser un usuario activo con rol de dueño de complejo.'},
    )
    nombre = TextoLimpioField(max_length=120)
    direccion = TextoLimpioField(max_length=160)
    latitud = _latitud()
    longitud = _longitud()
    telefono_contacto = TelefonoField(max_length=30, required=False, allow_blank=True, default='')
    horas_limite_cancelacion = serializers.IntegerField(min_value=0, max_value=168, default=4)
    info_sena = TextoLimpioField(max_length=200, required=False, allow_blank=True, default='')
    estado_contrato = serializers.ChoiceField(choices=ESTADOS_CONTRATO_INICIALES, default=EstadoContrato.PENDIENTE)


class ContratoEstadoSerializer(serializers.Serializer):
    estado_contrato = serializers.ChoiceField(choices=EstadoContrato.choices)


class UsuarioAdminSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='rol.nombre', read_only=True)
    complejo_operado_nombre = serializers.CharField(source='complejo_operado.nombre', read_only=True, default=None)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Usuario
        fields = (
            'id',
            'email',
            'nombre_completo',
            'telefono',
            'rol',
            'complejo_operado',
            'complejo_operado_nombre',
            'estado',
            'estado_nombre',
            'version_politica_aceptada',
            'fecha_aceptacion_politica',
            'fecha_creacion',
            'fecha_modificacion',
        )
        read_only_fields = fields


class UsuarioAdminEdicionSerializer(serializers.Serializer):
    nombre_completo = TextoLimpioField(max_length=120, required=False)
    telefono = TelefonoField(max_length=30, required=False, allow_blank=True)
    rol = serializers.SlugRelatedField(slug_field='nombre', queryset=RolRepository.activos(), required=False)
    complejo_operado = serializers.PrimaryKeyRelatedField(
        queryset=ComplejoRepository.vigentes(), allow_null=True, required=False,
    )
    estado = serializers.ChoiceField(choices=EstadoUsuario.choices, required=False)

    def validate(self, attrs):
        return _exigir_algun_campo(attrs)


class OperadorSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Usuario
        fields = ('id', 'nombre_completo', 'email', 'telefono', 'estado', 'estado_nombre')
        read_only_fields = fields


class VincularOperadorSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=120)

    def validate_email(self, valor):
        return valor.strip().lower()


ESTADOS_CANCHA_EDITABLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoCancha.choices if valor != EstadoCancha.BAJA
]


class CanchaSerializer(serializers.ModelSerializer):
    """El complejo se fija en el alta; la baja lógica se hace con DELETE y no editando el estado."""

    complejo = serializers.PrimaryKeyRelatedField(queryset=ComplejoRepository.vigentes())
    deporte = serializers.PrimaryKeyRelatedField(queryset=CatalogoRepository.deportes_activos())
    nombre = TextoLimpioField(max_length=80)
    precio_base = _precio()
    estado = serializers.ChoiceField(choices=ESTADOS_CANCHA_EDITABLES, required=False)
    deporte_nombre = serializers.CharField(source='deporte.nombre', read_only=True)
    tipo_superficie_nombre = serializers.CharField(source='get_tipo_superficie_display', read_only=True)
    cobertura_nombre = serializers.CharField(source='get_cobertura_display', read_only=True)
    iluminacion_nombre = serializers.CharField(source='get_iluminacion_display', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Cancha
        fields = (
            'id',
            'complejo',
            'deporte',
            'deporte_nombre',
            'nombre',
            'tipo_superficie',
            'tipo_superficie_nombre',
            'cobertura',
            'cobertura_nombre',
            'iluminacion',
            'iluminacion_nombre',
            'duracion_turno_min',
            'precio_base',
            'estado',
            'estado_nombre',
        )
        # La unicidad del nombre entre canchas vigentes la valida CanchaService.
        validators = []

    def get_fields(self):
        campos = super().get_fields()
        if isinstance(self.instance, Cancha):
            campos['complejo'] = serializers.PrimaryKeyRelatedField(read_only=True)
        return campos


class HorarioAperturaSerializer(serializers.ModelSerializer):
    """La cancha se fija en el alta; precio_diferenciado nulo indica que rige el precio_base de la cancha."""

    cancha = serializers.PrimaryKeyRelatedField(queryset=CanchaRepository.vigentes())
    precio_diferenciado = _precio(allow_null=True, required=False)
    dia_semana_nombre = serializers.CharField(source='get_dia_semana_display', read_only=True)

    class Meta:
        model = HorarioApertura
        fields = (
            'id',
            'cancha',
            'dia_semana',
            'dia_semana_nombre',
            'hora_apertura',
            'hora_cierre',
            'precio_diferenciado',
        )
        validators = []

    def get_fields(self):
        campos = super().get_fields()
        if isinstance(self.instance, HorarioApertura):
            campos['cancha'] = serializers.PrimaryKeyRelatedField(read_only=True)
        return campos

    def validate(self, attrs):
        apertura = attrs.get('hora_apertura', getattr(self.instance, 'hora_apertura', None))
        cierre = attrs.get('hora_cierre', getattr(self.instance, 'hora_cierre', None))
        if apertura is not None and cierre is not None and cierre <= apertura:
            raise serializers.ValidationError({'hora_cierre': 'Debe ser posterior a hora_apertura.'})
        return attrs
