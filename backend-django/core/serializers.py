import html
import re
import unicodedata
from decimal import Decimal

import nh3
from rest_framework import serializers

from .models import (
    HORAS_CANCELACION_DEFECTO,
    HORAS_CANCELACION_MAXIMAS,
    LARGO_DESCRIPCION_ROL,
    LARGO_ALIAS_MAXIMO,
    LARGO_ALIAS_MINIMO,
    LARGO_CBU,
    LARGO_DIRECCION,
    LARGO_EMAIL,
    LARGO_INFO_SENA,
    LARGO_MINIMO_NOMBRE,
    LARGO_MINIMO_PAGADOR,
    LARGO_MINIMO_REFERENCIA,
    LARGO_NOMBRE,
    LARGO_NOTA_RECHAZO,
    LARGO_NOMBRE_CANCHA,
    LARGO_NOMBRE_DEPORTE,
    LARGO_NOMBRE_ROL,
    LARGO_NOMBRE_SERVICIO,
    LARGO_PAGADOR_TRANSFERENCIA,
    LARGO_REFERENCIA_TRANSFERENCIA,
    LARGO_TELEFONO,
    LARGO_TEXTO_LIBRE,
    LARGO_TITULAR_TRANSFERENCIA,
    LATITUD_MAXIMA,
    LONGITUD_MAXIMA,
    PORCENTAJE_SENA_MAXIMO,
    AlcanceExcepcion,
    Cancha,
    Complejo,
    EstadoCancha,
    EstadoContrato,
    EstadoPago,
    EstadoRegistro,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    ExcepcionHoraria,
    HorarioApertura,
    LogAuditoria,
    MotivoRechazoTransferencia,
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
    CRITERIOS_REPORTE,
    ESTADOS_RESERVA_SENABLES,
    ROLES_BASE,
    ConflictoOperatoriaService,
    ReservaService,
    RolAdminService,
    TurnoFijoService,
)

MAXIMO_PASADAS_SANITIZACION = 5

PATRON_TELEFONO = re.compile(rf'^\+?[0-9\s()-]{{6,{LARGO_TELEFONO}}}$')
MENSAJE_TELEFONO = 'Ingresá un teléfono válido: solo números, espacios, guiones, paréntesis y un + inicial.'
MENSAJE_SIN_CAMPOS = 'Indicá al menos uno de los campos editables.'
# Nombre de persona: letras de cualquier idioma, espacios, apóstrofes, guiones y puntos ("María José", "O'Brien", "Jr.").
PATRON_NOMBRE_PERSONA = re.compile(r"^(?:[^\W\d_]|[ '’.\-])+$")
# Alias de CBU/CVU: entre 6 y 20 caracteres, solo letras, números, puntos y guiones, sin espacios. Se guarda en mayúsculas.
PATRON_ALIAS = re.compile(rf'^[A-Z0-9.\-]{{{LARGO_ALIAS_MINIMO},{LARGO_ALIAS_MAXIMO}}}$')
MENSAJE_ALIAS = (
    f'Ingresá un alias válido: entre {LARGO_ALIAS_MINIMO} y {LARGO_ALIAS_MAXIMO} caracteres, solo letras, números, '
    'puntos y guiones, sin espacios.'
)
# Quien transfirió puede ser una persona o una razón social: letras, números, espacios y . , & ' -.
PATRON_PAGADOR = re.compile(r"^[\w .,&'’\-]+$")
MENSAJE_PAGADOR = (
    f'Ingresá el nombre de quien transfirió: entre {LARGO_MINIMO_PAGADOR} y {LARGO_PAGADOR_TRANSFERENCIA} caracteres, '
    'solo letras, números, espacios y . , & \' -.'
)
# Número de operación: letras, números y . _ / - sin espacios, empezando por una letra o un número.
PATRON_REFERENCIA = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/\-]*$')
MENSAJE_REFERENCIA = (
    f'Ingresá el número de operación: entre {LARGO_MINIMO_REFERENCIA} y {LARGO_REFERENCIA_TRANSFERENCIA} caracteres, '
    'solo letras, números y . _ / - sin espacios.'
)
MENSAJE_CBU_LARGO = f'Ingresá los {LARGO_CBU} dígitos del CBU o CVU, solo números.'
MENSAJE_CBU_VERIFICADOR = 'El CBU o CVU no es válido: revisá los dígitos, porque los verificadores no coinciden.'
MENSAJE_NOMBRE_PERSONA = (
    'Ingresá un nombre válido: solo letras, espacios, apóstrofes, guiones y puntos, '
    f'entre {LARGO_MINIMO_NOMBRE} y {LARGO_NOMBRE} caracteres.'
)


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


def _digito_verificador(digitos, pesos):
    return (10 - sum(int(digito) * peso for digito, peso in zip(digitos, pesos)) % 10) % 10


def validar_cbu(valor):
    """
    Normaliza un CBU o CVU (se descartan espacios y guiones al pegarlo) y exige 22 dígitos con sus dos dígitos
    verificadores correctos: un error de tipeo mandaría las transferencias a otra cuenta. Vacío lo borra.
    """
    valor = re.sub(r'[\s-]', '', valor)
    if not valor:
        return valor
    if not re.fullmatch(rf'\d{{{LARGO_CBU}}}', valor):
        raise serializers.ValidationError(MENSAJE_CBU_LARGO)
    primero = _digito_verificador(valor[:7], (7, 1, 3, 9, 7, 1, 3))
    segundo = _digito_verificador(valor[8:21], (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3))
    if primero != int(valor[7]) or segundo != int(valor[21]):
        raise serializers.ValidationError(MENSAJE_CBU_VERIFICADOR)
    return valor


def validar_alias(valor):
    """Normaliza a mayúsculas y exige el formato de alias bancario o de billetera virtual; vacío limpia el alias."""
    valor = valor.upper()
    if valor and not PATRON_ALIAS.match(valor):
        raise serializers.ValidationError(MENSAJE_ALIAS)
    return valor


def validar_pagador(valor):
    """Colapsa los espacios y exige al menos dos letras y solo los caracteres de un nombre o una razón social."""
    valor = ' '.join(unicodedata.normalize('NFC', valor).split())
    letras = sum(caracter.isalpha() for caracter in valor)
    if letras < LARGO_MINIMO_PAGADOR or not PATRON_PAGADOR.match(valor):
        raise serializers.ValidationError(MENSAJE_PAGADOR)
    return valor


def validar_referencia(valor):
    valor = ' '.join(valor.split())
    if not PATRON_REFERENCIA.match(valor):
        raise serializers.ValidationError(MENSAJE_REFERENCIA)
    return valor


def validar_nombre_persona(valor):
    """Normaliza (acentos compuestos y espacios repetidos) y exige un nombre de persona sin dígitos, símbolos ni emojis."""
    valor = ' '.join(unicodedata.normalize('NFC', valor).split())
    letras = sum(caracter.isalpha() for caracter in valor)
    if letras < LARGO_MINIMO_NOMBRE or not valor[:1].isalpha() or not PATRON_NOMBRE_PERSONA.match(valor):
        raise serializers.ValidationError(MENSAJE_NOMBRE_PERSONA)
    return valor


class TextoLimpioField(serializers.CharField):
    def to_internal_value(self, data):
        valor = limpiar_texto(super().to_internal_value(data))
        if valor == '' and not self.allow_blank:
            self.fail('blank')
        return valor


class AliasField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_alias(super().to_internal_value(data))


class PagadorField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_pagador(super().to_internal_value(data))


class ReferenciaField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_referencia(super().to_internal_value(data))


class CbuField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_cbu(super().to_internal_value(data))


class NombrePersonaField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_nombre_persona(super().to_internal_value(data))


class TelefonoField(TextoLimpioField):
    def to_internal_value(self, data):
        return validar_telefono(super().to_internal_value(data))


def _exigir_algun_campo(attrs):
    if not attrs:
        raise serializers.ValidationError(MENSAJE_SIN_CAMPOS)
    return attrs


def _latitud(**opciones):
    return serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal(-LATITUD_MAXIMA), max_value=Decimal(LATITUD_MAXIMA),
        **opciones,
    )


def _longitud(**opciones):
    return serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal(-LONGITUD_MAXIMA), max_value=Decimal(LONGITUD_MAXIMA),
        **opciones,
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


class FiltroReporteSerializer(serializers.Serializer):
    complejo = serializers.IntegerField(min_value=1)
    fecha_desde = serializers.DateField(error_messages={'invalid': 'Usá el formato AAAA-MM-DD.'})
    fecha_hasta = serializers.DateField(error_messages={'invalid': 'Usá el formato AAAA-MM-DD.'})
    criterio = serializers.ChoiceField(choices=CRITERIOS_REPORTE, required=False)
    cancha_id = serializers.IntegerField(min_value=1, required=False)
    deporte_id = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        if attrs['fecha_desde'] > attrs['fecha_hasta']:
            raise serializers.ValidationError({'fecha_hasta': 'Debe ser igual o posterior a fecha_desde.'})
        return attrs


class CatalogoMaestroSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)


class NombreCatalogoField(TextoLimpioField):
    """Nombre de un catálogo maestro: sin etiquetas, sin espacios de más y con espacios internos simples."""

    def to_internal_value(self, data):
        return ' '.join(super().to_internal_value(data).split())


def _nombre_de_catalogo(largo_maximo, **opciones):
    return NombreCatalogoField(min_length=LARGO_MINIMO_NOMBRE, max_length=largo_maximo, **opciones)


class CatalogoMaestroAdminSerializer(serializers.Serializer):
    """Vista administrativa: incluye las bajas y cuántos registros vigentes usan cada ítem."""

    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    estado = serializers.IntegerField(read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    usos = serializers.IntegerField(read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_modificacion = serializers.DateTimeField(read_only=True)


class CatalogoMaestroEdicionSerializer(serializers.Serializer):
    """`estado` solo admite reactivar: la baja pasa por DELETE, que valida que el ítem no esté en uso."""

    estado = serializers.ChoiceField(choices=[EstadoRegistro.ACTIVO], required=False)

    def validate(self, attrs):
        return _exigir_algun_campo(attrs)


class UsoDeporteSerializer(serializers.Serializer):
    """Un complejo que usa el deporte, con sus canchas vigentes de ese deporte."""

    complejo_id = serializers.IntegerField(source='id', read_only=True)
    complejo_nombre = serializers.CharField(source='nombre', read_only=True)
    canchas = serializers.SerializerMethodField()

    def get_canchas(self, complejo):
        return [{'id': cancha.id, 'nombre': cancha.nombre} for cancha in complejo.canchas_del_deporte]


class UsoServicioSerializer(serializers.Serializer):
    complejo_id = serializers.IntegerField(source='id', read_only=True)
    complejo_nombre = serializers.CharField(source='nombre', read_only=True)


class UsoRolSerializer(serializers.Serializer):
    """Cuenta con el rol: lo justo para identificarla y abrirla en la gestión de usuarios (que ya expone estos datos)."""

    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(source='nombre_completo', read_only=True)
    email = serializers.CharField(read_only=True)
    estado = serializers.IntegerField(read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)


class DeporteAltaSerializer(serializers.Serializer):
    nombre = _nombre_de_catalogo(LARGO_NOMBRE_DEPORTE)


class DeporteEdicionSerializer(CatalogoMaestroEdicionSerializer):
    nombre = _nombre_de_catalogo(LARGO_NOMBRE_DEPORTE, required=False)


class ServicioAltaSerializer(serializers.Serializer):
    nombre = _nombre_de_catalogo(LARGO_NOMBRE_SERVICIO)


class ServicioEdicionSerializer(CatalogoMaestroEdicionSerializer):
    nombre = _nombre_de_catalogo(LARGO_NOMBRE_SERVICIO, required=False)


class IdsPermisoField(serializers.ListField):
    child = serializers.IntegerField(min_value=1)

    def to_internal_value(self, data):
        ids = super().to_internal_value(data)
        repetidos = sorted({permiso_id for permiso_id in ids if ids.count(permiso_id) > 1})
        if repetidos:
            raise serializers.ValidationError(f'No repitas permisos: {", ".join(map(str, repetidos))}.')
        return ids


class PermisoAdminSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    codigo = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    modulo = serializers.CharField(read_only=True)
    asignable = serializers.SerializerMethodField(help_text='False si es exclusivo de la plataforma.')

    def get_asignable(self, permiso):
        return RolAdminService.es_asignable(permiso)


class AsignacionPermisoSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='permiso_id', read_only=True)
    codigo = serializers.CharField(source='permiso.codigo', read_only=True)
    nombre = serializers.CharField(source='permiso.nombre', read_only=True)
    modulo = serializers.CharField(source='permiso.modulo', read_only=True)


class RolAdminSerializer(serializers.Serializer):
    """Vista administrativa: incluye las bajas, los permisos vigentes y cuántas cuentas usan cada rol."""

    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    descripcion = serializers.CharField(read_only=True)
    estado = serializers.IntegerField(read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    es_base = serializers.SerializerMethodField(help_text='True en los roles protegidos de la carga inicial.')
    usos = serializers.IntegerField(read_only=True)
    permisos = AsignacionPermisoSerializer(many=True, source='asignaciones_activas', read_only=True)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_modificacion = serializers.DateTimeField(read_only=True)

    def get_es_base(self, rol):
        return rol.nombre in ROLES_BASE


class RolAltaSerializer(serializers.Serializer):
    nombre = _nombre_de_catalogo(LARGO_NOMBRE_ROL)
    descripcion = TextoLimpioField(max_length=LARGO_DESCRIPCION_ROL, required=False, allow_blank=True)
    permisos = IdsPermisoField(required=False)


class RolEdicionSerializer(CatalogoMaestroEdicionSerializer):
    """`permisos` reemplaza la lista completa; `estado` solo admite reactivar (la baja pasa por DELETE)."""

    nombre = _nombre_de_catalogo(LARGO_NOMBRE_ROL, required=False)
    descripcion = TextoLimpioField(max_length=LARGO_DESCRIPCION_ROL, required=False, allow_blank=True)
    permisos = IdsPermisoField(required=False)


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
            'porcentaje_sena',
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


class MarcadorComplejoSerializer(serializers.ModelSerializer):
    """Lo mínimo que dibuja un marcador del mapa: sin propietario, contacto ni ningún dato personal."""

    precio_desde = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = Complejo
        fields = ('id', 'nombre', 'latitud', 'longitud', 'precio_desde')
        read_only_fields = fields


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
            'porcentaje_sena',
            'alias_transferencia',
            'titular_transferencia',
            'cbu_cvu_transferencia',
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
    nombre = TextoLimpioField(max_length=LARGO_NOMBRE, required=False)
    direccion = TextoLimpioField(max_length=LARGO_DIRECCION, required=False)
    latitud = _latitud(required=False)
    longitud = _longitud(required=False)
    telefono_contacto = TelefonoField(max_length=LARGO_TELEFONO, required=False, allow_blank=True)
    horas_limite_cancelacion = serializers.IntegerField(min_value=0, max_value=HORAS_CANCELACION_MAXIMAS, required=False)
    info_sena = TextoLimpioField(max_length=LARGO_INFO_SENA, required=False, allow_blank=True)
    porcentaje_sena = serializers.IntegerField(min_value=0, max_value=PORCENTAJE_SENA_MAXIMO, required=False)
    alias_transferencia = AliasField(max_length=LARGO_ALIAS_MAXIMO, required=False, allow_blank=True)
    titular_transferencia = TextoLimpioField(max_length=LARGO_TITULAR_TRANSFERENCIA, required=False, allow_blank=True)
    cbu_cvu_transferencia = CbuField(max_length=LARGO_CBU, required=False, allow_blank=True)

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
    nombre = TextoLimpioField(max_length=LARGO_NOMBRE)
    direccion = TextoLimpioField(max_length=LARGO_DIRECCION)
    latitud = _latitud()
    longitud = _longitud()
    telefono_contacto = TelefonoField(max_length=LARGO_TELEFONO, required=False, allow_blank=True, default='')
    horas_limite_cancelacion = serializers.IntegerField(min_value=0, max_value=HORAS_CANCELACION_MAXIMAS, default=HORAS_CANCELACION_DEFECTO)
    info_sena = TextoLimpioField(max_length=LARGO_INFO_SENA, required=False, allow_blank=True, default='')
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
    nombre_completo = TextoLimpioField(max_length=LARGO_NOMBRE, required=False)
    telefono = TelefonoField(max_length=LARGO_TELEFONO, required=False, allow_blank=True)
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
    email = serializers.EmailField(max_length=LARGO_EMAIL)

    def validate_email(self, valor):
        return valor.strip().lower()


ESTADOS_CANCHA_EDITABLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoCancha.choices if valor != EstadoCancha.BAJA
]


class CanchaSerializer(serializers.ModelSerializer):
    """El complejo se fija en el alta; la baja lógica se hace con DELETE y no editando el estado."""

    complejo = serializers.PrimaryKeyRelatedField(queryset=ComplejoRepository.vigentes())
    deporte = serializers.PrimaryKeyRelatedField(queryset=CatalogoRepository.deportes_activos())
    nombre = TextoLimpioField(max_length=LARGO_NOMBRE_CANCHA)
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
    descripcion = TextoLimpioField(max_length=LARGO_TEXTO_LIBRE, allow_blank=True, default='')
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
    nombre_cliente_manual = TextoLimpioField(max_length=LARGO_NOMBRE)
    telefono_cliente_manual = TelefonoField(max_length=LARGO_TELEFONO, allow_blank=True, default='')
    observaciones = TextoLimpioField(max_length=LARGO_TEXTO_LIBRE, allow_blank=True, default='')


class RechazoTransferenciaSerializer(serializers.Serializer):
    """Motivo de la lista y una nota corta opcional (se limpia de HTML) que ve el jugador en su reserva."""

    motivo = serializers.ChoiceField(choices=MotivoRechazoTransferencia.choices)
    nota = TextoLimpioField(max_length=LARGO_NOTA_RECHAZO, required=False, allow_blank=True, default='')


class TransferenciaInformadaSerializer(serializers.Serializer):
    """Quién transfirió la seña y el número de operación; ambos se limpian de HTML y se les colapsan los espacios."""

    titular = PagadorField(max_length=LARGO_PAGADOR_TRANSFERENCIA)
    referencia = ReferenciaField(max_length=LARGO_REFERENCIA_TRANSFERENCIA)

    def validate_referencia(self, valor):
        if len(valor) < LARGO_MINIMO_REFERENCIA:
            raise serializers.ValidationError(MENSAJE_REFERENCIA)
        return valor


ESTADOS_RESERVA_EDITABLES = [
    (valor, etiqueta) for valor, etiqueta in EstadoReserva.choices
    if valor in (
        EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA, EstadoReserva.AUSENTE,
        EstadoReserva.COMPLETADA,
    )
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
    observaciones = TextoLimpioField(max_length=LARGO_TEXTO_LIBRE, allow_blank=True, required=False)
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


CAMPOS_DE_PAGO = (
    'precio_acordado',
    'monto_sena',
    'monto_pagado',
    'saldo_restante',
    'estado_pago',
    'estado_pago_nombre',
    'transferencia_informada',
    'transferencia_rechazada',
    'transferencia',
)


class PagoReservaSerializer(serializers.ModelSerializer):
    """Montos congelados al reservar y estado de pago deducido de ellos; lo comparten el jugador y el personal."""

    saldo_restante = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    estado_pago = serializers.IntegerField(read_only=True)
    estado_pago_nombre = serializers.SerializerMethodField()
    transferencia_informada = serializers.BooleanField(read_only=True)
    transferencia_rechazada = serializers.BooleanField(read_only=True)
    transferencia = serializers.SerializerMethodField()

    def get_estado_pago_nombre(self, reserva):
        return EstadoPago(reserva.estado_pago).label

    def get_transferencia(self, reserva):
        """Lo que el jugador informó al transferir la seña; solo lo ven el titular y el personal de ese complejo."""
        if not reserva.transferencia_informada:
            return None
        rechazo = None
        if reserva.transferencia_rechazada:
            rechazo = {
                'motivo': reserva.transferencia_motivo_rechazo,
                'motivo_nombre': MotivoRechazoTransferencia(reserva.transferencia_motivo_rechazo).label,
                'nota': reserva.transferencia_nota_rechazo,
                'rechazada_en': serializers.DateTimeField().to_representation(reserva.transferencia_rechazada_en),
            }
        return {
            'titular': reserva.transferencia_titular,
            'referencia': reserva.transferencia_referencia,
            'informada_en': serializers.DateTimeField().to_representation(reserva.transferencia_informada_en),
            'rechazo': rechazo,
        }


class ReservaPropiaSerializer(PagoReservaSerializer):
    """
    Vista del jugador: no incluye las observaciones internas del complejo. Los datos de transferencia del complejo
    solo viajan mientras la seña está pendiente: es lo único para lo que el jugador los necesita.
    """

    complejo = serializers.SerializerMethodField()
    cancha = serializers.SerializerMethodField()
    deporte = serializers.CharField(source='cancha.deporte.nombre', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_ocupacion_nombre = serializers.CharField(source='get_tipo_ocupacion_display', read_only=True)
    cancelable_hasta = serializers.SerializerMethodField()
    datos_transferencia = serializers.SerializerMethodField()

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
            *CAMPOS_DE_PAGO,
            'datos_transferencia',
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

    def get_datos_transferencia(self, reserva):
        if reserva.estado not in ESTADOS_RESERVA_SENABLES or reserva.estado_pago != EstadoPago.SENA_PENDIENTE:
            return None
        complejo = reserva.cancha.complejo
        return {
            'alias': complejo.alias_transferencia,
            'titular': complejo.titular_transferencia,
            'cbu': complejo.cbu_cvu_transferencia,
        }


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


class ReservaAgendaSerializer(PagoReservaSerializer):
    """Vista del personal del complejo: incluye los datos de contacto que necesita la operatoria del predio."""

    complejo = serializers.IntegerField(source='cancha.complejo_id', read_only=True)
    cancha_nombre = serializers.CharField(source='cancha.nombre', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_ocupacion_nombre = serializers.CharField(source='get_tipo_ocupacion_display', read_only=True)
    cliente = serializers.SerializerMethodField()
    conflicto_operatoria = serializers.SerializerMethodField()
    puede_confirmar_sena = serializers.SerializerMethodField()
    puede_registrar_pago = serializers.SerializerMethodField()
    puede_anular_cobro = serializers.SerializerMethodField()

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
            *CAMPOS_DE_PAGO,
            'puede_confirmar_sena',
            'puede_registrar_pago',
            'puede_anular_cobro',
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

    def get_puede_confirmar_sena(self, reserva):
        return ReservaService.motivo_sena_no_registrable(reserva) is None

    def get_puede_registrar_pago(self, reserva):
        return ReservaService.motivo_pago_no_registrable(reserva) is None

    def get_puede_anular_cobro(self, reserva):
        return reserva.monto_pagado > 0

    def get_conflicto_operatoria(self, reserva):
        # El listado de la agenda lo trae anotado en SQL; una reserva suelta (alta, cambio de estado) se evalúa acá.
        if hasattr(reserva, 'motivo_conflicto'):
            return reserva.motivo_conflicto
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
    nombre_cliente_manual = TextoLimpioField(max_length=LARGO_NOMBRE)
    telefono_cliente_manual = TelefonoField(max_length=LARGO_TELEFONO, allow_blank=True, default='')
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
