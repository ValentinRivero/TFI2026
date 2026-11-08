"""
Pruebas de concurrencia sobre PostgreSQL: `select_for_update` no bloquea en SQLite. Hereda de settings_test
y solo cambia la base, que debe ser un PostgreSQL descartable (el servicio de CI o uno local): pytest-django
crea y destruye su propia base `test_<nombre>` en ese servidor.
"""
import os

from django.core.exceptions import ImproperlyConfigured

from .settings import _base_de_datos_desde_url
from .settings_test import *  # noqa: F401,F403

URL_POSTGRES_DE_PRUEBA = os.environ.get('TEST_POSTGRES_URL', '').strip()
if not URL_POSTGRES_DE_PRUEBA:
    raise ImproperlyConfigured(
        'Definí TEST_POSTGRES_URL con un PostgreSQL descartable para las pruebas de concurrencia.'
    )

DATABASES = {'default': _base_de_datos_desde_url(URL_POSTGRES_DE_PRUEBA)}
