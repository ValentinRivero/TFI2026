import os

from django.conf import settings
from django.db import connection
from django.test import TestCase


class EntornoDePruebasTests(TestCase):
    def test_usa_la_configuracion_de_tests(self):
        self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.settings_test')

    def test_base_de_pruebas_es_sqlite_en_memoria(self):
        self.assertEqual(connection.vendor, 'sqlite')
        self.assertIn('memory', str(connection.settings_dict['NAME']))

    def test_channel_layer_en_memoria(self):
        self.assertEqual(settings.CHANNEL_LAYERS['default']['BACKEND'], 'channels.layers.InMemoryChannelLayer')
