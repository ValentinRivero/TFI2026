import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .repositories import UsuarioRepository
from .serializers import TextoLimpioField
from .services import RbacService

Usuario = get_user_model()

PATRON_TELEFONO = re.compile(r'^\+?[0-9\s()-]{6,30}$')
MENSAJE_TELEFONO = 'Ingresá un teléfono válido: solo números, espacios, guiones, paréntesis y un + inicial.'
MENSAJE_POLITICA = 'Para usar TaLibre tenés que aceptar la política de privacidad.'


def _validar_telefono(valor):
    if valor and not PATRON_TELEFONO.match(valor):
        raise serializers.ValidationError(MENSAJE_TELEFONO)
    return valor


def _validar_aceptacion(valor):
    # El consentimiento tiene que ser expreso: un valor ausente o falso no lo reemplaza.
    if valor is not True:
        raise serializers.ValidationError(MENSAJE_POLITICA)
    return valor


class TokenConRolSerializer(TokenObtainPairSerializer):
    """Agrega al JWT el nombre del rol activo; el access lo hereda del refresh y lo leen backend-node y el frontend."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = RbacService.nombre_rol_activo(user)
        return token


class RegistroSerializer(serializers.Serializer):
    nombre_completo = TextoLimpioField(max_length=120)
    email = serializers.EmailField(max_length=120)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    telefono = TextoLimpioField(max_length=30, required=False, allow_blank=True, default='')
    acepta_politica_privacidad = serializers.BooleanField(
        write_only=True, error_messages={'required': MENSAJE_POLITICA},
    )

    def validate_email(self, valor):
        email = valor.strip().lower()
        if UsuarioRepository.existe_email(email):
            raise serializers.ValidationError('Ya existe una cuenta registrada con ese email.')
        return email

    def validate_telefono(self, valor):
        return _validar_telefono(valor)

    def validate_acepta_politica_privacidad(self, valor):
        return _validar_aceptacion(valor)

    def validate(self, attrs):
        candidato = Usuario(email=attrs['email'], nombre_completo=attrs['nombre_completo'])
        try:
            validate_password(attrs['password'], user=candidato)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=120)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_email(self, valor):
        return valor.strip().lower()


class PerfilSerializer(serializers.ModelSerializer):
    rol = serializers.SerializerMethodField()
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)
    debe_aceptar_politica = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            'id',
            'email',
            'nombre_completo',
            'telefono',
            'rol',
            'complejo_operado',
            'estado',
            'estado_nombre',
            'version_politica_aceptada',
            'fecha_aceptacion_politica',
            'debe_aceptar_politica',
            'fecha_creacion',
        )
        read_only_fields = fields

    def get_rol(self, usuario):
        return RbacService.nombre_rol_activo(usuario)

    def get_debe_aceptar_politica(self, usuario):
        return usuario.version_politica_aceptada != settings.POLITICA_PRIVACIDAD_VERSION


class PerfilEdicionSerializer(serializers.Serializer):
    nombre_completo = TextoLimpioField(max_length=120, required=False)
    telefono = TextoLimpioField(max_length=30, required=False, allow_blank=True)
    # Solo registra la aceptación de la versión vigente; retirar el consentimiento equivale a dar de baja la cuenta.
    acepta_politica_privacidad = serializers.BooleanField(required=False)

    def validate_telefono(self, valor):
        return _validar_telefono(valor)

    def validate_acepta_politica_privacidad(self, valor):
        return _validar_aceptacion(valor)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                'Indicá al menos uno de los campos editables: nombre_completo, telefono o acepta_politica_privacidad.'
            )
        return attrs
