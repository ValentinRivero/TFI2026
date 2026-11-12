import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def _env_bool(nombre, por_defecto=False):
    valor = os.environ.get(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')


def _env_lista(nombre, por_defecto=''):
    valor = os.environ.get(nombre, por_defecto)
    return [item.strip() for item in valor.split(',') if item.strip()]


def _env_obligatoria(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        raise ImproperlyConfigured(
            f'Falta la variable de entorno {nombre}. Definila en el archivo .env.'
        )
    return valor


def _base_de_datos_desde_url(url):
    partes = urlparse(url)
    if partes.scheme not in ('postgres', 'postgresql'):
        raise ImproperlyConfigured('DATABASE_URL debe usar el esquema postgres:// o postgresql://')

    opciones = dict(parse_qsl(partes.query))
    opciones.setdefault('sslmode', 'require')

    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(partes.path.lstrip('/')) or 'postgres',
        'USER': unquote(partes.username or ''),
        'PASSWORD': unquote(partes.password or ''),
        'HOST': partes.hostname or '',
        'PORT': str(partes.port or 5432),
        'OPTIONS': opciones,
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '0')),
        'CONN_HEALTH_CHECKS': True,
        # El pooler de Supabase en modo transacción (puerto 6543) no admite cursores del lado del servidor.
        'DISABLE_SERVER_SIDE_CURSORS': partes.port == 6543,
    }


SECRET_KEY = _env_obligatoria('DJANGO_SECRET_KEY')

DEBUG = _env_bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = _env_lista('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'graphene_django',
    'channels',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

if DATABASE_URL:
    DATABASES = {'default': _base_de_datos_desde_url(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'core.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('THROTTLE_ANON', '60/minute'),
        'user': os.environ.get('THROTTLE_USER', '240/minute'),
        'login': '5/minute',
        'registro': os.environ.get('THROTTLE_REGISTRO', '10/hour'),
        'reservas': '20/hour',
        'grilla': '300/minute',
        'graphql': os.environ.get('THROTTLE_GRAPHQL', '120/minute'),
    },
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += ('rest_framework.renderers.BrowsableAPIRenderer',)
    # JWT queda primero para que una petición sin credenciales reciba 401 y no 403.
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += ('rest_framework.authentication.SessionAuthentication',)

GRAPHENE = {
    'SCHEMA': 'config.schema.schema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_MINUTOS', '30'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_DIAS', '1'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    # Clave compartida con backend-node para validar el mismo token en ambos servicios.
    'SIGNING_KEY': _env_obligatoria('JWT_SIGNING_KEY'),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'usuario_id',
}

# Versión vigente de la política de privacidad publicada en el frontend; cambiarla obliga a aceptarla de nuevo.
POLITICA_PRIVACIDAD_VERSION = '1.0'

CORS_ALLOWED_ORIGINS = _env_lista(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173',
)
CSRF_TRUSTED_ORIGINS = _env_lista('CSRF_TRUSTED_ORIGINS', ','.join(CORS_ALLOWED_ORIGINS))
# La cookie HttpOnly del refresh solo viaja en peticiones cross-origin con credenciales habilitadas.
CORS_ALLOW_CREDENTIALS = True

# backend-node recibe los avisos de servidor por su ruta interna, autenticada con una clave compartida. Sin estas
# variables (o con una clave de menos de 32 caracteres) los avisos quedan en el log y nada falla.
NODE_API_URL = os.environ.get('NODE_API_URL', '').strip()
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY', '').strip()

REDIS_URL = os.environ.get('REDIS_URL', '').strip()

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        },
    }
    # Con varios procesos, los limitadores de peticiones necesitan contadores compartidos.
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        },
    }
else:
    # Sin Redis el channel layer y la caché viven en memoria: alcanza con un solo proceso de Daphne.
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

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

ARCHIVO_LOG_SEGURIDAD = BASE_DIR / 'security.log'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'seguridad': {
            'format': '{asctime} | {levelname} | {name} | {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'consola': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'archivo_seguridad': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': ARCHIVO_LOG_SEGURIDAD,
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'seguridad',
        },
    },
    'loggers': {
        'seguridad': {
            'handlers': ['archivo_seguridad', 'consola'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['archivo_seguridad', 'consola'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django': {
            'handlers': ['consola'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
        },
        # Fallas operativas del núcleo que no son de seguridad, como un channel layer caído.
        'core': {
            'handlers': ['consola'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
