import copy

from .settings import *  # noqa: F401,F403
from .settings import LOGGING as LOGGING_BASE

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

# Los parámetros operativos de las pruebas no dependen del .env local: se fijan en sus valores por defecto.
RESERVA_MESES_ANTICIPACION = 2
RANGO_MAXIMO_DIAS = 366
GRILLA_CACHE_SEGUNDOS = 60
NODE_TIMEOUT_SEGUNDOS = 3
CONTACTOS_BAJA_DIAS = 30
AUDITORIA_RETENCION_MESES = 12
CATALOGO_MARCADORES_MAXIMO = 500
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'NUM_PROXIES': 0,
    'DEFAULT_THROTTLE_RATES': {
        **REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'],  # noqa: F405
        'login': '5/minute',
        'reservas': '20/hour',
        'grilla': '300/minute',
    },
}

# MD5 solo acelera el hasheo en los tests; nunca se usa fuera de este módulo.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Los tests no escriben en el security.log real; el logger seguridad se verifica capturando sus registros.
LOGGING = copy.deepcopy(LOGGING_BASE)
LOGGING['handlers']['archivo_seguridad'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['consola'] = {'class': 'logging.NullHandler'}

# Los tests nunca entregan avisos a un backend-node real, aunque el .env local lo tenga configurado.
NODE_API_URL = ''
INTERNAL_API_KEY = ''
