from django.apps import apps
from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import Deporte, EstadoRegistro, LogAuditoria, Rol, Usuario


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre='SUPERADMIN')
        cls.superadmin = Usuario.objects.create_user(
            email='admin@irracional.net', password='ClaveSegura123', rol=rol, nombre_completo='Admin Test',
        )

    def setUp(self):
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.superadmin

    def _modelos_core(self):
        return apps.get_app_config('core').get_models()

    def test_las_14_tablas_estan_registradas(self):
        for modelo in self._modelos_core():
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(admin.site.is_registered(modelo))

    def test_ninguna_tabla_permite_borrado_fisico(self):
        for modelo in self._modelos_core():
            modelo_admin = admin.site._registry[modelo]
            with self.subTest(modelo=modelo.__name__):
                self.assertFalse(modelo_admin.has_delete_permission(self.request))
                self.assertNotIn('delete_selected', modelo_admin.get_actions(self.request))

    def test_accion_desactivar_aplica_baja_logica_sin_borrar_fila(self):
        deporte = Deporte.objects.create(nombre='Hockey')
        self.client.force_login(self.superadmin)

        respuesta = self.client.post(
            reverse('admin:core_deporte_changelist'),
            {'action': 'desactivar_seleccionados', '_selected_action': [deporte.pk]},
        )

        self.assertEqual(respuesta.status_code, 302)
        deporte.refresh_from_db()
        self.assertEqual(deporte.estado, EstadoRegistro.BAJA)
        self.assertTrue(Deporte.objects.filter(pk=deporte.pk).exists())

    def test_log_auditoria_es_de_solo_lectura(self):
        modelo_admin = admin.site._registry[LogAuditoria]
        self.assertFalse(modelo_admin.has_add_permission(self.request))
        self.assertFalse(modelo_admin.has_change_permission(self.request))
        self.assertEqual(dict(modelo_admin.get_actions(self.request)), {})

    def test_formulario_de_usuario_no_expone_password(self):
        formulario = admin.site._registry[Usuario].get_form(self.request)
        self.assertNotIn('password', formulario.base_fields)
