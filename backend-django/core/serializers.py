import html
import re
from decimal import Decimal

import nh3
from rest_framework import serializers

from .models import (
    AlcanceExcepcion,
    Cancha,
    Complejo,
    EstadoCancha,
    EstadoContrato,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    ExcepcionHoraria,
    HorarioApertura,
    LogAuditoria,
    Reserva,
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
    TurnoFijo,
    Usuario,
)
from .repositories import CanchaRepository, CatalogoRepository, ComplejoRepository, RolRepository, UsuarioRepository
from .services import (
    ACCION_CANCELAR_FECHA,
    ACCION_MANTENER_FECHA,
    ConflictoOperatoriaService,
    ReservaService,
    TurnoFijoService,
)

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


class ExcepcionHorariaSerializer(serializers.ModelSerializer):
    """
    Sin cancha, la excepción cierra todo el complejo. No hay edición: una excepción mal cargada se da de baja
    y se registra otra, así la auditoría conserva cada versión.
    """

    complejo = serializers.PrimaryKeyRelatedField(queryset=ComplejoRepository.vigentes())
    cancha = serializers.PrimaryKeyRelatedField(queryset=CanchaRepository.vigentes(), allow_null=True, default=None)
    es_dia_completo = serializers.ChoiceField(choices=AlcanceExcepcion.choices)
    hora_inicio = serializers.TimeField(allow_null=True, default=None)
    hora_fin = serializers.TimeField(allow_null=True, default=None)
    tipo_motivo = serializers.ChoiceField(choices=TipoMotivoExcepcion.choices)
    descripcion = TextoLimpioField(max_length=255, allow_blank=True, default='')
    cancha_nombre = serializers.CharField(source='cancha.nombre', read_only=True, default=None)
    es_dia_completo_nombre = serializers.CharField(source='get_es_dia_completo_display', read_only=True)
    tipo_motivo_nombre = serializers.CharField(source='get_tipo_motivo_display', read_only=True)

    class Meta:
        model = ExcepcionHoraria
        fields = (
            'id',
            'complejo',
            'cancha',
            'cancha_nombre',
            'fecha_inicio',
            'fecha_fin',
            'es_dia_completo',
            'es_dia_completo_nombre',
            'hora_inicio',
            'hora_fin',
            'tipo_motivo',
            'tipo_motivo_nombre',
            'descripcion',
            'fecha_creacion',
        )
        read_only_fields = ('fecha_creacion',)
        validators = []

    def validate(self, attrs):
        errores = {}
        if attrs['fecha_fin'] < attrs['fecha_inicio']:
            errores['fecha_fin'] = 'Debe ser igual o posterior a fecha_inicio.'

        inicio, fin = attrs.get('hora_inicio'), attrs.get('hora_fin')
        if attrs['es_dia_completo'] == AlcanceExcepcion.DIA_COMPLETO:
            if inicio is not None or fin is not None:
                errores['hora_inicio'] = 'Una excepción de día completo no lleva horario.'
        else:
            if inicio is None:
                errores['hora_inicio'] = 'Es obligatoria en una franja horaria.'
            if fin is None:
                errores['hora_fin'] = 'Es obligatoria en una franja horaria.'
            if inicio is not None and fin is not None and fin <= inicio:
                errores['hora_fin'] = 'Debe ser posterior a hora_inicio.'

        if errores:
            raise serializers.ValidationError(errores)
        return attrs


class FiltroGrillaSerializer(serializers.Serializer):
    fecha = serializers.DateField(
        error_messages={'invalid': 'Usá el formato AAAA-MM-DD.', 'required': 'Indicá la fecha a consultar.'},
    )


class BloqueGrillaSerializer(serializers.Serializer):
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()
    precio = serializers.DecimalField(max_digits=10, decimal_places=2)
    estado = serializers.CharField()
    motivo = serializers.CharField(allow_null=True)


class CanchaGrillaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    deporte = CatalogoMaestroSerializer()
    duracion_turno_min = serializers.IntegerField()
    bloques = BloqueGrillaSerializer(many=True)


class GrillaSerializer(serializers.Serializer):
    """Respuesta pública: solo horarios, precios y estados; ninguna ocupación identifica a su titular."""

    complejo = CatalogoMaestroSerializer()
    fecha = serializers.DateField()
    dia_semana = serializers.IntegerField()
    canchas = CanchaGrillaSerializer(many=True)


MENSAJES_FECHA_ISO = {'invalid': 'Usá el formato AAAA-MM-DD.'}
MENSAJES_HORA = {'invalid': 'Usá el formato HH:MM.'}


class ReservaAltaSerializer(serializers.Serializer):
    """hora_fin y precio_acordado no se reciben: los calcula el servidor a partir de la cancha y su horario."""

    cancha = serializers.PrimaryKeyRelatedField(queryset=CanchaRepository.vigentes())
    fecha_turno = serializers.DateField(error_messages=MENSAJES_FECHA_ISO)
    hora_inicio = serializers.TimeField(error_messages=MENSAJES_HORA)


class ReservaManualSerializer(ReservaAltaSerializer):
    nombre_cliente_manual = TextoLimpioField(max_length=120)
    telefono_cliente_manual = TelefonoField(max_length=30, allow_blank=True, default='')
    observaciones = TextoLimpioField(max_length=255, allow_blank=True, default='')


ESTADOS_RESERVA_EDITABLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoReserva.choices
    if valor in (EstadoReserva.CONFIRMADA, EstadoReserva.SENADA, EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA)
]


class CamposInmutablesMixin:
    """
    Un campo que no se edita y llega con otro valor responde 400 con el motivo, en lugar de ignorarse en
    silencio; si llega con el mismo valor (un formulario que reenvía todo) se descarta sin error.
    """

    campos_inmutables = {}

    def descartar_inmutables(self, attrs):
        if self.instance is None:
            return attrs
        errores = {
            campo: mensaje for campo, mensaje in self.campos_inmutables.items()
            if campo in attrs and attrs[campo] != getattr(self.instance, campo)
        }
        if errores:
            raise serializers.ValidationError(errores)
        return {campo: valor for campo, valor in attrs.items() if campo not in self.campos_inmutables}


MENSAJE_TURNO_NO_EDITABLE = 'No se edita: cancelá la reserva y registrá otra.'


class ReservaAgendaEdicionSerializer(CamposInmutablesMixin, serializers.Serializer):
    """Las cancelaciones tienen su propia ruta; acá solo se confirma, se seña o se cierra el turno."""

    estado = serializers.ChoiceField(choices=ESTADOS_RESERVA_EDITABLES, required=False)
    observaciones = TextoLimpioField(max_length=255, allow_blank=True, required=False)
    cancha = serializers.PrimaryKeyRelatedField(queryset=CanchaRepository.vigentes(), required=False)
    fecha_turno = serializers.DateField(required=False, error_messages=MENSAJES_FECHA_ISO)
    hora_inicio = serializers.TimeField(required=False, error_messages=MENSAJES_HORA)
    hora_fin = serializers.TimeField(required=False, error_messages=MENSAJES_HORA)
    precio_acordado = _precio(required=False)

    campos_inmutables = {
        'cancha': MENSAJE_TURNO_NO_EDITABLE,
        'fecha_turno': MENSAJE_TURNO_NO_EDITABLE,
        'hora_inicio': MENSAJE_TURNO_NO_EDITABLE,
        'hora_fin': MENSAJE_TURNO_NO_EDITABLE,
        'precio_acordado': 'El precio acordado lo fija el horario de la cancha al registrar la reserva.',
    }

    def validate(self, attrs):
        return _exigir_algun_campo(self.descartar_inmutables(attrs))


class ReservaPropiaSerializer(serializers.ModelSerializer):
    """Vista del jugador: no incluye las observaciones internas del complejo."""

    complejo = serializers.SerializerMethodField()
    cancha = serializers.SerializerMethodField()
    deporte = serializers.CharField(source='cancha.deporte.nombre', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_ocupacion_nombre = serializers.CharField(source='get_tipo_ocupacion_display', read_only=True)
    cancelable_hasta = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = (
            'id',
            'complejo',
            'cancha',
            'deporte',
            'fecha_turno',
            'hora_inicio',
            'hora_fin',
            'precio_acordado',
            'tipo_ocupacion',
            'tipo_ocupacion_nombre',
            'estado',
            'estado_nombre',
            'cancelable_hasta',
            'fecha_creacion',
        )
        read_only_fields = fields

    def get_complejo(self, reserva):
        return {'id': reserva.cancha.complejo_id, 'nombre': reserva.cancha.complejo.nombre}

    def get_cancha(self, reserva):
        return {'id': reserva.cancha_id, 'nombre': reserva.cancha.nombre}

    def get_cancelable_hasta(self, reserva):
        return serializers.DateTimeField().to_representation(ReservaService.limite_de_cancelacion(reserva))


TITULAR_DADO_DE_BAJA = 'Titular dado de baja'


def _datos_de_contacto(ocupacion):
    """
    Contacto de quien ocupa el turno: la cuenta del jugador si reservó en la web, o el cliente cargado a mano.
    Si el titular se dio de baja, se muestra solo la copia conservada para resolver la seña (o nada): nunca su
    cuenta anonimizada.
    """
    usuario = ocupacion.usuario
    if usuario is not None and usuario.estado != EstadoUsuario.BAJA:
        return {'nombre': usuario.nombre_completo, 'telefono': usuario.telefono, 'email': usuario.email}
    nombre = ocupacion.nombre_cliente_manual or (TITULAR_DADO_DE_BAJA if usuario is not None else '')
    return {'nombre': nombre, 'telefono': ocupacion.telefono_cliente_manual, 'email': None}


class ReservaAgendaSerializer(serializers.ModelSerializer):
    """Vista del personal del complejo: incluye los datos de contacto que necesita la operatoria del predio."""

    complejo = serializers.IntegerField(source='cancha.complejo_id', read_only=True)
    cancha_nombre = serializers.CharField(source='cancha.nombre', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_ocupacion_nombre = serializers.CharField(source='get_tipo_ocupacion_display', read_only=True)
    cliente = serializers.SerializerMethodField()
    conflicto_operatoria = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = (
            'id',
            'complejo',
            'cancha',
            'cancha_nombre',
            'fecha_turno',
            'hora_inicio',
            'hora_fin',
            'precio_acordado',
            'tipo_ocupacion',
            'tipo_ocupacion_nombre',
            'turno_fijo',
            'estado',
            'estado_nombre',
            'cliente',
            'observaciones',
            'conflicto_operatoria',
            'fecha_creacion',
            'fecha_modificacion',
        )
        read_only_fields = fields

    def get_cliente(self, reserva):
        return _datos_de_contacto(reserva)

    def get_conflicto_operatoria(self, reserva):
        return ConflictoOperatoriaService.motivo_de_reserva(reserva)


ESTADOS_TURNO_FIJO_EDITABLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoTurnoFijo.choices if valor != EstadoTurnoFijo.BAJA
]


MENSAJE_TURNO_FIJO_NO_EDITABLE = 'No se edita: dá de baja el turno fijo y registrá otro.'


class TurnoFijoSerializer(CamposInmutablesMixin, serializers.ModelSerializer):
    """
    hora_fin la calcula el servidor según la duración del turno de la cancha. La cancha, el día, el horario y el
    inicio de la vigencia se fijan en el alta; la baja lógica se hace con DELETE.
    """

    # El horario sí se edita (con confirmación): TurnoFijoService.actualizar recalcula hora_fin y revalida.
    campos_inmutables = {
        'cancha': MENSAJE_TURNO_FIJO_NO_EDITABLE,
        'dia_semana': MENSAJE_TURNO_FIJO_NO_EDITABLE,
        'fecha_inicio_vigencia': MENSAJE_TURNO_FIJO_NO_EDITABLE,
    }

    cancha = serializers.PrimaryKeyRelatedField(queryset=CanchaRepository.vigentes())
    hora_inicio = serializers.TimeField(error_messages=MENSAJES_HORA)
    fecha_inicio_vigencia = serializers.DateField(error_messages=MENSAJES_FECHA_ISO)
    fecha_fin_vigencia = serializers.DateField(allow_null=True, default=None, error_messages=MENSAJES_FECHA_ISO)
    nombre_cliente_manual = TextoLimpioField(max_length=120)
    telefono_cliente_manual = TelefonoField(max_length=30, allow_blank=True, default='')
    estado = serializers.ChoiceField(choices=ESTADOS_TURNO_FIJO_EDITABLES, required=False)
    cancha_nombre = serializers.CharField(source='cancha.nombre', read_only=True)
    dia_semana_nombre = serializers.CharField(source='get_dia_semana_display', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    cliente = serializers.SerializerMethodField()
    conflicto_operatoria = serializers.SerializerMethodField()
    fechas_en_espera = serializers.SerializerMethodField()

    class Meta:
        model = TurnoFijo
        fields = (
            'id',
            'cancha',
            'cancha_nombre',
            'dia_semana',
            'dia_semana_nombre',
            'hora_inicio',
            'hora_fin',
            'fecha_inicio_vigencia',
            'fecha_fin_vigencia',
            'nombre_cliente_manual',
            'telefono_cliente_manual',
            'cliente',
            'estado',
            'estado_nombre',
            'conflicto_operatoria',
            'fechas_en_espera',
            'fecha_creacion',
        )
        read_only_fields = ('hora_fin', 'fecha_creacion')
        validators = []

    def get_fields(self):
        campos = super().get_fields()
        if not isinstance(self.instance, TurnoFijo):
            # Un turno fijo nace vigente; se pausa o se reanuda después con PATCH.
            campos['estado'] = serializers.IntegerField(read_only=True)
        return campos

    def validate(self, attrs):
        return self.descartar_inmutables(attrs)

    def get_cliente(self, turno_fijo):
        return _datos_de_contacto(turno_fijo)

    def get_conflicto_operatoria(self, turno_fijo):
        return ConflictoOperatoriaService.motivo_de_turno_fijo(turno_fijo)

    def get_fechas_en_espera(self, turno_fijo):
        # El listado las calcula para toda la página de una vez; el detalle, para un solo turno fijo.
        precalculadas = self.context.get('fechas_en_espera')
        if precalculadas is None:
            precalculadas = TurnoFijoService.fechas_en_espera([turno_fijo])
        return precalculadas.get(turno_fijo.pk, [])


class ConfirmacionSerializer(serializers.Serializer):
    """`confirmar: true` aplica un cambio de operatoria aunque deje reservas o turnos fijos fuera de la grilla."""

    confirmar = serializers.BooleanField(default=False)


ACCIONES_FECHA_TURNO_FIJO = [
    (ACCION_MANTENER_FECHA, 'Mantener la fecha (se juega)'),
    (ACCION_CANCELAR_FECHA, 'Cancelar la fecha y liberar el casillero'),
]


class FechaTurnoFijoSerializer(serializers.Serializer):
    fecha_turno = serializers.DateField(error_messages=MENSAJES_FECHA_ISO)
    accion = serializers.ChoiceField(choices=ACCIONES_FECHA_TURNO_FIJO, default=ACCION_MANTENER_FECHA)


ESTADOS_DE_REAPERTURA = [
    (valor, etiqueta) for valor, etiqueta in EstadoReserva.choices
    if valor in (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA)
]


class ReaperturaSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=ESTADOS_DE_REAPERTURA)
    confirmar = serializers.BooleanField(default=False)
