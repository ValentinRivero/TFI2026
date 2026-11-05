import os
from io import StringIO
from unittest import mock

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from core.models import (
    AlcanceExcepcion,
    Cancha,
    Complejo,
    Deporte,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    EstadoUsuario,
    ExcepcionHoraria,
    LogAuditoria,
    ModeloBase,
    Permiso,
    Reserva,
    Rol,
    RolPermiso,
    Servicio,
    TipoEventoAuditoria,
    TipoOcupacion,
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
            email='baja@irracional.net', password='ClaveSegura123', rol=rol, nombre_completo='Usuario Baja',
        )
        self.assertTrue(usuario.is_active)
        usuario.desactivar()
        usuario.refresh_from_db()
        self.assertEqual(usuario.estado, EstadoUsuario.BAJA)
        self.assertFalse(usuario.is_active)

    def test_usuario_suspendido_queda_inactivo(self):
        rol = Rol.objects.create(nombre='JUGADOR')
        usuario = Usuario.objects.create_user(
            email='suspendido@irracional.net', password='ClaveSegura123', rol=rol, nombre_completo='Usuario Suspendido',
        )
        usuario.estado = EstadoUsuario.SUSPENDIDO
        usuario.save(update_fields=['estado', 'fecha_modificacion'])
        self.assertFalse(usuario.is_active)


@mock.patch.dict(os.environ, {'SEED_PASSWORD_DEMO': 'ClaveDemoTest2026'})
class SeedInicialTests(TestCase):
    def _ejecutar_seed(self):
        call_command('seed_inicial', stdout=StringIO())

    def test_carga_roles_permisos_y_asignaciones(self):
        self._ejecutar_seed()
        self.assertEqual(
            set(Rol.objects.values_list('nombre', flat=True)),
            {'SUPERADMIN', 'DUENO_COMPLEJO', 'OPERADOR_COMPLEJO', 'JUGADOR'},
        )
        codigos = set(Permiso.objects.values_list('codigo', flat=True))
        self.assertTrue(
            {
                'reservar_turno',
                'configurar_complejo',
                'administrar_canchas',
                'gestionar_agenda',
                'gestionar_excepciones',
                'ver_reportes',
                'administrar_contratos',
                'auditar_seguridad',
            }.issubset(codigos)
        )
        superadmin = Rol.objects.get(nombre='SUPERADMIN')
        self.assertEqual(RolPermiso.objects.filter(rol=superadmin).count(), len(codigos))

    def _permisos_de(self, nombre_rol):
        return set(RolPermiso.objects.filter(rol__nombre=nombre_rol).values_list('permiso__codigo', flat=True))

    def test_todos_los_roles_gestionan_su_perfil_propio(self):
        self._ejecutar_seed()
        perfil = {'ver_perfil_propio', 'editar_perfil_propio', 'desactivar_perfil_propio'}
        for nombre_rol in ('SUPERADMIN', 'DUENO_COMPLEJO', 'OPERADOR_COMPLEJO', 'JUGADOR'):
            with self.subTest(rol=nombre_rol):
                self.assertTrue(perfil.issubset(self._permisos_de(nombre_rol)))

    def test_operador_edita_perfil_del_complejo_sin_acciones_del_dueno(self):
        self._ejecutar_seed()
        permisos = self._permisos_de('OPERADOR_COMPLEJO')
        self.assertIn('configurar_complejo', permisos)
        self.assertIn('gestionar_agenda', permisos)
        self.assertTrue(
            permisos.isdisjoint({'administrar_canchas', 'administrar_precios', 'gestionar_operadores', 'ver_reportes'})
        )

    def test_jugador_no_accede_a_paneles_ni_a_otros_usuarios(self):
        self._ejecutar_seed()
        self.assertEqual(
            self._permisos_de('JUGADOR'),
            {
                'ver_perfil_propio',
                'editar_perfil_propio',
                'desactivar_perfil_propio',
                'reservar_turno',
                'ver_reservas_propias',
                'cancelar_reserva_propia',
            },
        )

    def test_gestion_de_otros_usuarios_solo_para_superadmin(self):
        self._ejecutar_seed()
        for nombre_rol in ('DUENO_COMPLEJO', 'OPERADOR_COMPLEJO', 'JUGADOR'):
            with self.subTest(rol=nombre_rol):
                self.assertTrue(
                    self._permisos_de(nombre_rol).isdisjoint(
                        {'ver_usuarios', 'editar_usuarios', 'desactivar_usuarios', 'ver_panel_sistema'}
                    )
                )

    def test_nuevo_rol_admite_permisos_especificos(self):
        self._ejecutar_seed()
        rol = Rol.objects.create(nombre='RECEPCIONISTA', descripcion='Solo consulta la agenda.')
        for codigo in ('ver_panel_complejo', 'ver_agenda'):
            RolPermiso.objects.create(rol=rol, permiso=Permiso.objects.get(codigo=codigo))
        self.assertEqual(self._permisos_de('RECEPCIONISTA'), {'ver_panel_complejo', 'ver_agenda'})

    def test_datos_respetan_largos_y_opciones_de_los_campos(self):
        # SQLite no exige max_length, pero PostgreSQL sí: se valida para que el seed no falle en Supabase.
        self._ejecutar_seed()
        for modelo in apps.get_app_config('core').get_models():
            for instancia in modelo.objects.all():
                with self.subTest(modelo=modelo.__name__, pk=instancia.pk):
                    instancia.clean_fields()

    def test_excepciones_usan_alcance_numerico(self):
        self._ejecutar_seed()
        self.assertEqual(
            set(ExcepcionHoraria.objects.values_list('es_dia_completo', flat=True)),
            {AlcanceExcepcion.DIA_COMPLETO, AlcanceExcepcion.FRANJA_HORARIA},
        )

    def test_es_idempotente(self):
        self._ejecutar_seed()
        conteos = [modelo.objects.count() for modelo in apps.get_app_config('core').get_models()]
        self._ejecutar_seed()
        conteos_repetidos = [modelo.objects.count() for modelo in apps.get_app_config('core').get_models()]
        self.assertEqual(conteos, conteos_repetidos)

    def test_correos_demo_usan_dominio_irracional(self):
        self._ejecutar_seed()
        self.assertTrue(Usuario.objects.filter(email='talibre@irracional.net', rol__nombre='SUPERADMIN').exists())
        self.assertFalse(Usuario.objects.exclude(email__endswith='@irracional.net').exists())

    def test_complejos_tienen_propietario_y_contratos(self):
        self._ejecutar_seed()
        self.assertFalse(Complejo.objects.filter(propietario__isnull=True).exists())
        self.assertTrue(Complejo.objects.filter(estado_contrato=EstadoContrato.ACTIVO).exists())
        self.assertTrue(Complejo.objects.filter(estado_contrato=EstadoContrato.PENDIENTE).exists())

    def test_operador_queda_vinculado_a_su_complejo(self):
        self._ejecutar_seed()
        operador = Usuario.objects.get(email='lucas.benitez@irracional.net')
        self.assertEqual(operador.rol.nombre, 'OPERADOR_COMPLEJO')
        self.assertEqual(operador.complejo_operado.nombre, 'Complejo El Potrero')
        self.assertIn(operador, operador.complejo_operado.operadores.all())

    def test_turnos_fijos_generan_reservas_vinculadas(self):
        self._ejecutar_seed()
        self.assertTrue(TurnoFijo.objects.exists())
        for turno in TurnoFijo.objects.all():
            reservas = Reserva.objects.filter(turno_fijo=turno)
            self.assertTrue(reservas.exists())
            self.assertFalse(reservas.exclude(tipo_ocupacion=TipoOcupacion.TURNO_FIJO).exists())
            self.assertFalse(reservas.exclude(estado=EstadoReserva.CONFIRMADA).exists())

    def test_login_con_usuario_demo(self):
        self._ejecutar_seed()
        self.assertTrue(
            self.client.login(email='talibre@irracional.net', password='ClaveDemoTest2026')
        )

    def test_sin_demo_carga_solo_catalogos(self):
        call_command('seed_inicial', '--sin-demo', stdout=StringIO())
        self.assertEqual(Rol.objects.count(), 4)
        self.assertTrue(Deporte.objects.exists())
        self.assertFalse(Usuario.objects.exists())
        self.assertFalse(Complejo.objects.exists())
