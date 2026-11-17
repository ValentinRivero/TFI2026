import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase, TestCase, override_settings

RAIZ_DJANGO = Path(__file__).resolve().parents[2]
VARIABLES_DE_CONFIGURACION = (
    'DJANGO_DEBUG', 'SECURE_SSL_REDIRECT', 'SECURE_HSTS_SEGUNDOS', 'DATABASE_URL', 'REDIS_URL', 'SECURITY_LOG_PATH',
)


class ConfiguracionDeProduccionTests(SimpleTestCase):
    def test_check_deploy_no_deja_pendientes(self):
        entorno = {clave: valor for clave, valor in os.environ.items() if clave not in VARIABLES_DE_CONFIGURACION}
        entorno.update({
            'DJANGO_SECRET_KEY': 'k8Qz!w3Vn0xP-t7Lm2Rj9Yb5Hd1Sa6Fg4Cu8Ei3Oo0Pp7Zz2Xx5Ww9Vv1Bb4Nn6',
            'JWT_SIGNING_KEY': 'clave-de-firma-solo-para-la-verificacion-0123456789',
            'DJANGO_DEBUG': 'False',
            'DJANGO_ALLOWED_HOSTS': 'talibre.test',
            'DATABASE_URL': '',
            'REDIS_URL': '',
            'SECURITY_LOG_PATH': os.devnull,
        })
        resultado = subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING', '--settings=config.settings'],
            cwd=RAIZ_DJANGO, env=entorno, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn('no issues', resultado.stdout)


@override_settings(
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
    ALLOWED_HOSTS=['talibre.test', 'web', 'testserver'],
)
class RedireccionAHttpsTests(TestCase):
    def test_una_ruta_publica_por_http_se_redirige_a_https(self):
        respuesta = self.client.get('/api/complejos/', secure=False)
        self.assertEqual(respuesta.status_code, 301)
        self.assertTrue(respuesta['Location'].startswith('https://'))

    def test_con_el_encabezado_del_proxy_no_se_redirige(self):
        respuesta = self.client.get('/api/health/', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(respuesta.status_code, 200)

    def test_el_healthcheck_responde_por_http_dentro_de_la_red_privada(self):
        respuesta = self.client.get('/api/health/')
        self.assertEqual(respuesta.status_code, 200)

    def test_el_detalle_de_un_complejo_que_consulta_node_no_se_redirige(self):
        for ruta in ('/api/complejos/7/', '/api/complejos/7/acceso/'):
            with self.subTest(ruta=ruta):
                self.assertNotEqual(self.client.get(ruta).status_code, 301)

    def test_el_resto_del_detalle_de_complejos_si_se_redirige(self):
        self.assertEqual(self.client.get('/api/complejos/7/grilla/').status_code, 301)
