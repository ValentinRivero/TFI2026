import html

import nh3
from rest_framework import serializers

from .models import LogAuditoria, TipoEventoAuditoria

MAXIMO_PASADAS_SANITIZACION = 5


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


class TextoLimpioField(serializers.CharField):
    def to_internal_value(self, data):
        valor = limpiar_texto(super().to_internal_value(data))
        if valor == '' and not self.allow_blank:
            self.fail('blank')
        return valor


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
