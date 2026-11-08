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

# MD5 solo acelera el hasheo en los tests; nunca se usa fuera de este módulo.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Los tests no escriben en el security.log real; el logger seguridad se verifica capturando sus registros.
LOGGING = copy.deepcopy(LOGGING_BASE)
LOGGING['handlers']['archivo_seguridad'] = {'class': 'logging.NullHandler'}
LOGGING['handlers']['consola'] = {'class': 'logging.NullHandler'}
