from django.apps import apps
from django.db import connection
from django.test import TestCase

from core.models import (
    Cancha,
    Complejo,
    Deporte,
    EstadoRegistro,
    EstadoUsuario,
    ExcepcionHoraria,
    LogAuditoria,
    ModeloBase,
    Permiso,
    Reserva,
    Rol,
    Servicio,
    TipoEventoAuditoria,
    TurnoFijo,
    Usuario,
)

TABLAS_ESPERADAS = {
    'roles',
    'permisos',
    'roles_permisos',
    'usuarios',
    'complejos',
    'servicios',
    'complejos_servicios',
    'deportes',
    'canchas',
    'horarios_apertura',
    'excepciones_horarias',
    'turnos_fijos',
    'reservas',
    'logs_auditoria',
}


class EsquemaTests(TestCase):
    def test_existen_las_14_tablas(self):
        tablas_bd = set(connection.introspection.table_names())
        self.assertTrue(TABLAS_ESPERADAS.issubset(tablas_bd), TABLAS_ESPERADAS - tablas_bd)

    def test_core_define_exactamente_14_modelos(self):
        tablas_core = {modelo._meta.db_table for modelo in apps.get_app_config('core').get_models()}
        self.assertEqual(tablas_core, TABLAS_ESPERADAS)

    def test_modelos_de_negocio_heredan_modelo_base(self):
        for modelo in apps.get_app_config('core').get_models():
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(issubclass(modelo, ModeloBase))
                nombres = {campo.name for campo in modelo._meta.get_fields()}
                self.assertTrue({'estado', 'fecha_creacion', 'fecha_modificacion'}.issubset(nombres))

    def test_log_conserva_fecha_de_la_accion_tras_baja_logica(self):
        nombres = {campo.name for campo in LogAuditoria._meta.get_fields()}
        self.assertNotIn('fecha_accion', nombres)
        self.assertNotIn('fecha_evento', nombres)

        log = LogAuditoria.objects.create(
            tipo_evento=TipoEventoAuditoria.LOGIN_FALLIDO,
            accion='Intento de login fallido',
            ip_origen='127.0.0.1',
        )
        fecha_accion = log.fecha_creacion

        log.desactivar()
        log.refresh_from_db()

        self.assertEqual(log.estado, EstadoRegistro.BAJA)
        self.assertEqual(log.fecha_creacion, fecha_accion)

    def test_estado_y_fecha_creacion_estan_indexados(self):
        for modelo in apps.get_app_config('core').get_models():
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(modelo._meta.get_field('estado').db_index)
                self.assertTrue(modelo._meta.get_field('fecha_creacion').db_index)

    def test_estados_propios_de_cada_entidad(self):
        esperados = {
            Usuario: {0, 1, 2},
            Cancha: {0, 1, 2},
            TurnoFijo: {0, 1, 2},
            Reserva: {0, 1, 2, 3, 4, 5, 6, 7},
        }
        for modelo, valores in esperados.items():
            with self.subTest(modelo=modelo.__name__):
                opciones = {valor for valor, _ in modelo._meta.get_field('estado').choices}
                self.assertEqual(opciones, valores)

    def test_campos_alineados_con_project_md(self):
        largos = [
            (Rol, 'nombre', 50), (Rol, 'descripcion', 150),
            (Permiso, 'codigo', 60), (Permiso, 'nombre', 100), (Permiso, 'modulo', 50),
            (Usuario, 'nombre_completo', 120), (Usuario, 'email', 120), (Usuario, 'telefono', 30),
            (Complejo, 'info_sena', 200), (Servicio, 'nombre', 80), (Deporte, 'nombre', 60),
        ]
        for modelo, campo, largo in largos:
            with self.subTest(modelo=modelo.__name__, campo=campo):
                self.assertEqual(modelo._meta.get_field(campo).max_length, largo)

        self.assertEqual(
            ExcepcionHoraria._meta.get_field('es_dia_completo').get_internal_type(),
            'SmallIntegerField',
        )
        self.assertEqual(
            Complejo._meta.get_field('horas_limite_cancelacion').get_internal_type(),
            'SmallIntegerField',
        )
        self.assertEqual(Complejo._meta.get_field('horas_limite_cancelacion').default, 4)
        self.assertEqual(Complejo._meta.get_field('propietario').remote_field.related_name, 'complejos_propios')

    def test_usuario_tiene_complejo_operado_y_no_last_login(self):
        nombres = {campo.name for campo in Usuario._meta.get_fields()}
        self.assertIn('complejo_operado', nombres)
        self.assertNotIn('complejo', nombres)
        self.assertNotIn('last_login', nombres)


class ModeloBaseTests(TestCase):
    def test_estado_por_defecto_es_activo(self):
        deporte = Deporte.objects.create(nombre='Hockey')
        self.assertEqual(deporte.estado, EstadoRegistro.ACTIVO)
        self.assertIsNotNone(deporte.fecha_creacion)
        self.assertIsNotNone(deporte.fecha_modificacion)

    def test_desactivar_aplica_baja_logica_sin_borrar_fila(self):
        deporte = Deporte.objects.create(nombre='Handball')
        modificacion_original = deporte.fecha_modificacion

        deporte.desactivar()
        deporte.refresh_from_db()

        self.assertEqual(deporte.estado, EstadoRegistro.BAJA)
        self.assertGreaterEqual(deporte.fecha_modificacion, modificacion_original)
        self.assertTrue(Deporte.objects.filter(pk=deporte.pk).exists())

    def test_usuario_dado_de_baja_queda_inactivo(self):
        rol = Rol.objects.create(nombre='JUGADOR')
        usuario = Usuario.objects.create_user(
            email='baja@talibre.test', password='ClaveSegura123', rol=rol, nombre_completo='Usuario Baja',
        )
        self.assertTrue(usuario.is_active)
        usuario.desactivar()
        usuario.refresh_from_db()
        self.assertEqual(usuario.estado, EstadoUsuario.BAJA)
        self.assertFalse(usuario.is_active)

    def test_usuario_suspendido_queda_inactivo(self):
        rol = Rol.objects.create(nombre='JUGADOR')
        usuario = Usuario.objects.create_user(
            email='suspendido@talibre.test', password='ClaveSegura123', rol=rol, nombre_completo='Usuario Suspendido',
        )
        usuario.estado = EstadoUsuario.SUSPENDIDO
        usuario.save(update_fields=['estado', 'fecha_modificacion'])
        self.assertFalse(usuario.is_active)
