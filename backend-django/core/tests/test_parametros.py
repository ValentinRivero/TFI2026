"""
Parámetros operativos de config/settings.py: valores por defecto, lectura del entorno y rechazo de valores inválidos.

Cada caso ejecuta una copia nueva de settings.py con el entorno controlado, sin leer el .env local, así los
valores por defecto que se comprueban no dependen de quien corre las pruebas.
"""
import importlib.util
import pathlib

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

from core.services import AuditoriaService
from core.throttles import LoginRateThrottle

RUTA_SETTINGS = pathlib.Path(__file__).resolve().parents[2] / 'config' / 'settings.py'

VARIABLES_DE_ENTORNO = (
    'DJANGO_SECRET_KEY', 'DJANGO_DEBUG', 'DJANGO_ALLOWED_HOSTS', 'DATABASE_URL', 'DB_CONN_MAX_AGE',
    'THROTTLE_ANON', 'THROTTLE_USER', 'THROTTLE_LOGIN', 'THROTTLE_REGISTRO', 'THROTTLE_RESERVAS',
    'THROTTLE_GRILLA', 'THROTTLE_GRAPHQL', 'NUM_PROXIES', 'JWT_ACCESS_MINUTOS', 'JWT_REFRESH_DIAS',
    'JWT_SIGNING_KEY', 'CORS_ALLOWED_ORIGINS', 'CSRF_TRUSTED_ORIGINS', 'NODE_API_URL', 'INTERNAL_API_KEY',
    'REDIS_URL', 'DJANGO_LOG_LEVEL', 'RESERVA_MESES_ANTICIPACION', 'RANGO_MAXIMO_DIAS', 'GRILLA_CACHE_SEGUNDOS',
    'NODE_TIMEOUT_SEGUNDOS', 'CONTACTOS_BAJA_DIAS', 'AUDITORIA_RETENCION_MESES', 'CATALOGO_MARCADORES_MAXIMO',
    'DATA_UPLOAD_MAX_MEMORY_SIZE', 'DATA_UPLOAD_MAX_NUMBER_FIELDS', 'CACHE_TIMEOUT_SEGUNDOS', 'CHANNEL_CAPACITY',
    'CHANNEL_EXPIRY_SEGUNDOS', 'CHANNEL_GROUP_EXPIRY_SEGUNDOS',
)


@pytest.fixture
def cargar_settings(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *args, **kwargs: False)

    def _cargar(**entorno):
        for nombre in VARIABLES_DE_ENTORNO:
            monkeypatch.delenv(nombre, raising=False)
        monkeypatch.setenv('DJANGO_SECRET_KEY', 'clave-de-prueba')
        monkeypatch.setenv('JWT_SIGNING_KEY', 'clave-jwt-de-prueba')
        for nombre, valor in entorno.items():
            monkeypatch.setenv(nombre, str(valor))
        especificacion = importlib.util.spec_from_file_location('settings_aislado', RUTA_SETTINGS)
        modulo = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(modulo)
        return modulo

    return _cargar


ESCALARES_POR_DEFECTO = {
    'RESERVA_MESES_ANTICIPACION': 2,
    'RANGO_MAXIMO_DIAS': 366,
    'GRILLA_CACHE_SEGUNDOS': 60,
    'NODE_TIMEOUT_SEGUNDOS': 3,
    'CONTACTOS_BAJA_DIAS': 30,
    'AUDITORIA_RETENCION_MESES': 12,
    'CATALOGO_MARCADORES_MAXIMO': 500,
    'DATA_UPLOAD_MAX_MEMORY_SIZE': 2_621_440,
    'DATA_UPLOAD_MAX_NUMBER_FIELDS': 1000,
    'CACHE_TIMEOUT_SEGUNDOS': 300,
}

TASAS_POR_DEFECTO = {
    'anon': '60/minute',
    'user': '240/minute',
    'login': '5/minute',
    'registro': '10/hour',
    'reservas': '20/hour',
    'grilla': '300/minute',
    'graphql': '120/minute',
}


class TestValoresPorDefecto:
    @pytest.mark.parametrize('nombre, esperado', ESCALARES_POR_DEFECTO.items())
    def test_parametro_escalar(self, cargar_settings, nombre, esperado):
        assert getattr(cargar_settings(), nombre) == esperado

    def test_tasas_de_peticiones(self, cargar_settings):
        assert cargar_settings().REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] == TASAS_POR_DEFECTO

    def test_sin_proxies_de_confianza(self, cargar_settings):
        assert cargar_settings().REST_FRAMEWORK['NUM_PROXIES'] == 0

    def test_tamano_de_pagina(self, cargar_settings):
        assert cargar_settings().REST_FRAMEWORK['PAGE_SIZE'] == 20

    def test_vida_de_los_tokens(self, cargar_settings):
        jwt = cargar_settings().SIMPLE_JWT
        assert jwt['ACCESS_TOKEN_LIFETIME'].total_seconds() == 30 * 60
        assert jwt['REFRESH_TOKEN_LIFETIME'].total_seconds() == 24 * 3600

    def test_capa_de_canales_y_cache_en_memoria(self, cargar_settings):
        modulo = cargar_settings()
        assert modulo.CHANNEL_LAYERS['default']['BACKEND'] == 'channels.layers.InMemoryChannelLayer'
        assert modulo.CHANNEL_LAYERS['default']['CONFIG'] == {'capacity': 100, 'expiry': 60, 'group_expiry': 86400}
        assert modulo.CACHES['default']['TIMEOUT'] == 300

    def test_una_variable_vacia_usa_el_valor_por_defecto(self, cargar_settings):
        modulo = cargar_settings(RANGO_MAXIMO_DIAS='  ', THROTTLE_LOGIN='')
        assert modulo.RANGO_MAXIMO_DIAS == 366
        assert modulo.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] == '5/minute'


class TestLecturaDelEntorno:
    @pytest.mark.parametrize('nombre, valor', [
        ('RESERVA_MESES_ANTICIPACION', 3),
        ('RANGO_MAXIMO_DIAS', 90),
        ('GRILLA_CACHE_SEGUNDOS', 30),
        ('NODE_TIMEOUT_SEGUNDOS', 5),
        ('CONTACTOS_BAJA_DIAS', 15),
        ('AUDITORIA_RETENCION_MESES', 6),
        ('CATALOGO_MARCADORES_MAXIMO', 100),
        ('DATA_UPLOAD_MAX_MEMORY_SIZE', 65_536),
        ('DATA_UPLOAD_MAX_NUMBER_FIELDS', 200),
        ('CACHE_TIMEOUT_SEGUNDOS', 120),
    ])
    def test_parametro_escalar(self, cargar_settings, nombre, valor):
        assert getattr(cargar_settings(**{nombre: valor}), nombre) == valor

    @pytest.mark.parametrize('variable, scope', [
        ('THROTTLE_ANON', 'anon'),
        ('THROTTLE_USER', 'user'),
        ('THROTTLE_LOGIN', 'login'),
        ('THROTTLE_REGISTRO', 'registro'),
        ('THROTTLE_RESERVAS', 'reservas'),
        ('THROTTLE_GRILLA', 'grilla'),
        ('THROTTLE_GRAPHQL', 'graphql'),
    ])
    def test_tasas_de_peticiones(self, cargar_settings, variable, scope):
        tasas = cargar_settings(**{variable: '7/hour'}).REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        assert tasas[scope] == '7/hour'
        assert {clave: valor for clave, valor in tasas.items() if clave != scope} == {
            clave: valor for clave, valor in TASAS_POR_DEFECTO.items() if clave != scope
        }

    def test_proxies_de_confianza(self, cargar_settings):
        assert cargar_settings(NUM_PROXIES=1).REST_FRAMEWORK['NUM_PROXIES'] == 1

    def test_vida_de_los_tokens(self, cargar_settings):
        jwt = cargar_settings(JWT_ACCESS_MINUTOS=10, JWT_REFRESH_DIAS=7).SIMPLE_JWT
        assert jwt['ACCESS_TOKEN_LIFETIME'].total_seconds() == 10 * 60
        assert jwt['REFRESH_TOKEN_LIFETIME'].total_seconds() == 7 * 24 * 3600

    def test_capa_de_canales_en_memoria(self, cargar_settings):
        modulo = cargar_settings(CHANNEL_CAPACITY=50, CHANNEL_EXPIRY_SEGUNDOS=30, CHANNEL_GROUP_EXPIRY_SEGUNDOS=600)
        assert modulo.CHANNEL_LAYERS['default']['CONFIG'] == {'capacity': 50, 'expiry': 30, 'group_expiry': 600}

    def test_con_redis_la_capa_de_canales_y_la_cache_usan_los_parametros(self, cargar_settings):
        modulo = cargar_settings(REDIS_URL='redis://redis:6379/0', CHANNEL_CAPACITY=50, CACHE_TIMEOUT_SEGUNDOS=120)

        assert modulo.CHANNEL_LAYERS['default']['BACKEND'] == 'channels_redis.core.RedisChannelLayer'
        assert modulo.CHANNEL_LAYERS['default']['CONFIG'] == {
            'hosts': ['redis://redis:6379/0'], 'capacity': 50, 'expiry': 60, 'group_expiry': 86400,
        }
        assert modulo.CACHES['default']['TIMEOUT'] == 120


class TestValoresInvalidos:
    @pytest.mark.parametrize('nombre, valor', [
        ('RESERVA_MESES_ANTICIPACION', 'dos'),
        ('RESERVA_MESES_ANTICIPACION', '0'),
        ('RESERVA_MESES_ANTICIPACION', '25'),
        ('RANGO_MAXIMO_DIAS', '1.5'),
        ('RANGO_MAXIMO_DIAS', '-1'),
        ('RANGO_MAXIMO_DIAS', '3661'),
        ('GRILLA_CACHE_SEGUNDOS', '0'),
        ('NODE_TIMEOUT_SEGUNDOS', '31'),
        ('CONTACTOS_BAJA_DIAS', '366'),
        ('AUDITORIA_RETENCION_MESES', '0'),
        ('CATALOGO_MARCADORES_MAXIMO', '5001'),
        ('DATA_UPLOAD_MAX_MEMORY_SIZE', '10'),
        ('DATA_UPLOAD_MAX_NUMBER_FIELDS', '1'),
        ('CACHE_TIMEOUT_SEGUNDOS', '0'),
        ('CHANNEL_CAPACITY', '0'),
        ('CHANNEL_EXPIRY_SEGUNDOS', 'abc'),
        ('CHANNEL_GROUP_EXPIRY_SEGUNDOS', '59'),
        ('NUM_PROXIES', '-1'),
        ('NUM_PROXIES', '11'),
        ('JWT_ACCESS_MINUTOS', '0'),
        ('JWT_REFRESH_DIAS', 'uno'),
    ])
    def test_un_entero_fuera_de_rango_corta_el_arranque_con_el_nombre_de_la_variable(
        self, cargar_settings, nombre, valor,
    ):
        with pytest.raises(ImproperlyConfigured, match=nombre):
            cargar_settings(**{nombre: valor})

    @pytest.mark.parametrize('variable', [
        'THROTTLE_ANON', 'THROTTLE_USER', 'THROTTLE_LOGIN', 'THROTTLE_REGISTRO',
        'THROTTLE_RESERVAS', 'THROTTLE_GRILLA', 'THROTTLE_GRAPHQL',
    ])
    @pytest.mark.parametrize('valor', ['cinco/minute', '0/minute', '5', '5/', '5/minuto/dia', '-3/hour', '5/Minute'])
    def test_una_tasa_con_formato_invalido_corta_el_arranque(self, cargar_settings, variable, valor):
        with pytest.raises(ImproperlyConfigured, match=variable):
            cargar_settings(**{variable: valor})


class TestIdentificacionDeLaIp:
    """Con 0 proxies de confianza, un X-Forwarded-For enviado por el cliente no cambia la IP de los límites."""

    def _pedido(self, **cabeceras):
        return RequestFactory().get('/api/token/', REMOTE_ADDR='198.51.100.9', **cabeceras)

    def test_sin_proxies_se_usa_la_ip_de_la_conexion(self, settings):
        settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, 'NUM_PROXIES': 0}
        pedido = self._pedido(HTTP_X_FORWARDED_FOR='203.0.113.50, 203.0.113.51')

        assert LoginRateThrottle().get_ident(pedido) == '198.51.100.9'
        assert AuditoriaService.ip_de_request(pedido) == '198.51.100.9'

    def test_con_un_proxy_se_usa_el_ultimo_salto_agregado_por_el_proxy(self, settings):
        settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, 'NUM_PROXIES': 1}
        pedido = self._pedido(HTTP_X_FORWARDED_FOR='203.0.113.50, 203.0.113.51')

        assert LoginRateThrottle().get_ident(pedido) == '203.0.113.51'
        assert AuditoriaService.ip_de_request(pedido) == '203.0.113.51'
