import logging
from decimal import Decimal
from io import StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

PASSWORD_PRUEBA = 'CanchaLibre#2026'


@pytest.fixture(autouse=True)
def cache_limpia():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def rbac(db):
    """Roles, permisos y asignaciones reales de seed_inicial, sin datos de demostración."""
    call_command('seed_inicial', '--sin-demo', stdout=StringIO())


@pytest.fixture
def crear_usuario(rbac):
    from core.models import Rol, Usuario

    def _crear(email, rol='JUGADOR', password=PASSWORD_PRUEBA, **campos):
        campos.setdefault('nombre_completo', 'Usuario de Prueba')
        return Usuario.objects.create_user(
            email=email, password=password, rol=Rol.objects.get(nombre=rol), **campos,
        )

    return _crear


@pytest.fixture
def crear_complejo(db):
    from core.models import Complejo, EstadoContrato

    def _crear(propietario, nombre='Complejo de Prueba', **campos):
        campos.setdefault('estado_contrato', EstadoContrato.ACTIVO)
        campos.setdefault('direccion', 'Calle Los Aromos 100, Goya')
        campos.setdefault('latitud', Decimal('-29.140000'))
        campos.setdefault('longitud', Decimal('-59.260000'))
        return Complejo.objects.create(propietario=propietario, nombre=nombre, **campos)

    return _crear


@pytest.fixture
def crear_cancha(rbac):
    from core.models import Cancha, Cobertura, Deporte, Iluminacion, TipoSuperficie

    def _crear(complejo, nombre='Cancha 1', deporte='Fútbol 5', **campos):
        campos.setdefault('tipo_superficie', TipoSuperficie.CESPED_SINTETICO)
        campos.setdefault('cobertura', Cobertura.DESCUBIERTA)
        campos.setdefault('iluminacion', Iluminacion.LED)
        campos.setdefault('precio_base', Decimal('38000.00'))
        return Cancha.objects.create(
            complejo=complejo, nombre=nombre, deporte=Deporte.objects.get(nombre=deporte), **campos,
        )

    return _crear


@pytest.fixture
def ofrecer_servicios(rbac):
    from core.models import ComplejoServicio, Servicio

    def _ofrecer(complejo, *nombres):
        return [
            ComplejoServicio.objects.create(complejo=complejo, servicio=Servicio.objects.get(nombre=nombre))
            for nombre in nombres
        ]

    return _ofrecer


@pytest.fixture
def jugador(crear_usuario):
    return crear_usuario('jugador@talibre.test', 'JUGADOR', nombre_completo='Jugador Prueba')


@pytest.fixture
def dueno(crear_usuario):
    return crear_usuario('dueno@talibre.test', 'DUENO_COMPLEJO', nombre_completo='Dueño Prueba')


@pytest.fixture
def otro_dueno(crear_usuario):
    return crear_usuario('otro.dueno@talibre.test', 'DUENO_COMPLEJO', nombre_completo='Otro Dueño')


@pytest.fixture
def superadmin(crear_usuario):
    return crear_usuario('superadmin@talibre.test', 'SUPERADMIN', nombre_completo='Superadmin Prueba')


@pytest.fixture
def complejo(crear_complejo, dueno):
    return crear_complejo(dueno, 'Complejo Propio')


@pytest.fixture
def complejo_ajeno(crear_complejo, otro_dueno):
    return crear_complejo(otro_dueno, 'Complejo Ajeno')


@pytest.fixture
def operador(crear_usuario, complejo):
    return crear_usuario(
        'operador@talibre.test', 'OPERADOR_COMPLEJO', nombre_completo='Operador Prueba', complejo_operado=complejo,
    )


@pytest.fixture
def cliente_de():
    """Devuelve un APIClient autenticado con un access token real del usuario."""
    from core.serializers_auth import TokenConRolSerializer

    def _cliente(usuario):
        api = APIClient()
        token = TokenConRolSerializer.get_token(usuario).access_token
        api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return api

    return _cliente


@pytest.fixture
def log_seguridad(caplog):
    """El logger seguridad no propaga a la raíz: se le engancha el handler de captura de pytest."""
    logger = logging.getLogger('seguridad')
    logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger='seguridad')
    yield caplog
    logger.removeHandler(caplog.handler)
