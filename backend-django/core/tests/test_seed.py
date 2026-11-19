import os
from datetime import date, time, timedelta
from io import StringIO
from unittest import mock

from django.apps import apps
from django.core.management import CommandError, call_command
from django.test import TestCase

from core.models import (
    AlcanceExcepcion,
    Complejo,
    Deporte,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    ExcepcionHoraria,
    HorarioApertura,
    Permiso,
    Reserva,
    Rol,
    RolPermiso,
    TipoOcupacion,
    TurnoFijo,
    Usuario,
)


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
        self.assertEqual(
            RolPermiso.objects.filter(rol=superadmin, estado=EstadoRegistro.ACTIVO).count(),
            len(codigos),
        )

    def _permisos_de(self, nombre_rol):
        return set(
            RolPermiso.objects.filter(rol__nombre=nombre_rol, estado=EstadoRegistro.ACTIVO)
            .values_list('permiso__codigo', flat=True)
        )

    def test_todos_los_roles_gestionan_su_perfil_propio(self):
        self._ejecutar_seed()
        perfil = {'ver_perfil_propio', 'editar_perfil_propio', 'desactivar_perfil_propio'}
        for nombre_rol in ('SUPERADMIN', 'DUENO_COMPLEJO', 'OPERADOR_COMPLEJO', 'JUGADOR'):
            with self.subTest(rol=nombre_rol):
                self.assertTrue(perfil.issubset(self._permisos_de(nombre_rol)))

    def test_operador_gestiona_la_operatoria_diaria_sin_acciones_del_dueno(self):
        self._ejecutar_seed()
        permisos = self._permisos_de('OPERADOR_COMPLEJO')
        self.assertTrue(
            {'ver_panel_complejo', 'gestionar_agenda', 'gestionar_turnos_fijos', 'gestionar_excepciones'}.issubset(permisos)
        )
        self.assertTrue(
            permisos.isdisjoint(
                {'configurar_complejo', 'administrar_canchas', 'administrar_precios', 'gestionar_operadores', 'ver_reportes'}
            )
        )

    def test_configurar_complejo_solo_para_dueno_y_superadmin(self):
        self._ejecutar_seed()
        roles = set(
            RolPermiso.objects.filter(permiso__codigo='configurar_complejo', estado=EstadoRegistro.ACTIVO)
            .values_list('rol__nombre', flat=True)
        )
        self.assertEqual(roles, {'DUENO_COMPLEJO', 'SUPERADMIN'})

    def test_resincroniza_asignaciones_con_baja_logica(self):
        self._ejecutar_seed()
        operador = Rol.objects.get(nombre='OPERADOR_COMPLEJO')
        asignacion_vieja = RolPermiso.objects.create(
            rol=operador, permiso=Permiso.objects.get(codigo='configurar_complejo'),
        )
        asignacion_vigente = RolPermiso.objects.get(rol=operador, permiso__codigo='gestionar_agenda')
        asignacion_vigente.desactivar()

        self._ejecutar_seed()

        asignacion_vieja.refresh_from_db()
        asignacion_vigente.refresh_from_db()
        self.assertEqual(asignacion_vieja.estado, EstadoRegistro.BAJA)
        self.assertEqual(asignacion_vigente.estado, EstadoRegistro.ACTIVO)
        self.assertNotIn('configurar_complejo', self._permisos_de('OPERADOR_COMPLEJO'))

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

    def test_es_idempotente_aunque_un_dia_tenga_cortes(self):
        self._ejecutar_seed()
        cancha = Reserva.objects.filter(turno_fijo__isnull=False).first().cancha
        primero = HorarioApertura.objects.filter(cancha=cancha, dia_semana=0, estado=EstadoRegistro.ACTIVO).get()
        corte = time(primero.hora_apertura.hour - 1, 0)
        HorarioApertura.objects.create(
            cancha=cancha, dia_semana=0, hora_apertura=time(corte.hour - 2, 0), hora_cierre=corte,
        )
        horarios = HorarioApertura.objects.count()

        self._ejecutar_seed()

        self.assertEqual(HorarioApertura.objects.count(), horarios)

    def test_correos_demo_usan_un_dominio_reservado(self):
        self._ejecutar_seed()
        self.assertTrue(Usuario.objects.filter(email='superadmin@demo.talibre.test', rol__nombre='SUPERADMIN').exists())
        self.assertFalse(Usuario.objects.exclude(email__endswith='@demo.talibre.test').exists())

    def test_complejos_tienen_propietario_y_contratos(self):
        self._ejecutar_seed()
        self.assertFalse(Complejo.objects.filter(propietario__isnull=True).exists())
        self.assertTrue(Complejo.objects.filter(estado_contrato=EstadoContrato.ACTIVO).exists())
        self.assertTrue(Complejo.objects.filter(estado_contrato=EstadoContrato.PENDIENTE).exists())

    def test_operador_queda_vinculado_a_su_complejo(self):
        self._ejecutar_seed()
        operador = Usuario.objects.get(email='elias.mendieta@demo.talibre.test')
        self.assertEqual(operador.rol.nombre, 'OPERADOR_COMPLEJO')
        self.assertEqual(operador.complejo_operado.nombre, 'Complejo El Yacaré')
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
            self.client.login(email='superadmin@demo.talibre.test', password='ClaveDemoTest2026')
        )

    def test_sin_demo_carga_solo_catalogos(self):
        call_command('seed_inicial', '--sin-demo', stdout=StringIO())
        self.assertEqual(Rol.objects.count(), 4)
        self.assertTrue(Deporte.objects.exists())
        self.assertFalse(Usuario.objects.exists())
        self.assertFalse(Complejo.objects.exists())


@mock.patch.dict(os.environ, {'SEED_PASSWORD_DEMO': 'ClaveDemoTest2026'})
class SeedAgendaRelativaTests(TestCase):
    def _ejecutar(self, hoy, *argumentos):
        with mock.patch('core.management.commands.seed_inicial.timezone.localdate', return_value=hoy):
            call_command('seed_inicial', *argumentos, stdout=StringIO())

    def _agenda_activa(self):
        return (
            Reserva.objects.exclude(estado=EstadoReserva.BAJA).count(),
            TurnoFijo.objects.exclude(estado=EstadoRegistro.BAJA).count(),
            ExcepcionHoraria.objects.exclude(estado=EstadoRegistro.BAJA).count(),
        )

    def test_las_fechas_de_la_agenda_se_calculan_a_partir_de_hoy(self):
        hoy = date(2027, 3, 10)
        self._ejecutar(hoy)

        fechas = list(Reserva.objects.values_list('fecha_turno', flat=True))
        fechas += list(ExcepcionHoraria.objects.values_list('fecha_inicio', flat=True))
        fechas += list(TurnoFijo.objects.values_list('fecha_inicio_vigencia', flat=True))
        self.assertTrue(fechas)
        for fecha in fechas:
            self.assertLessEqual(abs((fecha - hoy).days), 30)
        self.assertTrue(Reserva.objects.filter(estado=EstadoReserva.COMPLETADA, fecha_turno__lt=hoy).exists())
        self.assertTrue(Reserva.objects.filter(estado=EstadoReserva.CONFIRMADA, fecha_turno__gt=hoy).exists())

    def test_cada_dia_de_la_semana_genera_la_misma_agenda_sin_choques(self):
        self._ejecutar(date(2027, 3, 8))
        esperada = self._agenda_activa()
        for dia in range(9, 16):
            with self.subTest(hoy=date(2027, 3, dia)):
                self._ejecutar(date(2027, 3, dia), '--reset')
                self.assertEqual(self._agenda_activa(), esperada)
                for turno in TurnoFijo.objects.exclude(estado=EstadoRegistro.BAJA):
                    reservas = Reserva.objects.filter(turno_fijo=turno).exclude(estado=EstadoReserva.BAJA)
                    self.assertTrue(reservas.exists())
                    for reserva in reservas:
                        self.assertEqual(reserva.fecha_turno.weekday(), turno.dia_semana)

    def test_los_turnos_fijos_caen_en_su_dia_de_la_semana(self):
        self._ejecutar(date(2027, 3, 10))
        for turno in TurnoFijo.objects.all():
            self.assertEqual(turno.fecha_inicio_vigencia.weekday(), turno.dia_semana)

    def test_repetir_el_seed_conserva_las_reservas_cargadas_despues(self):
        self._ejecutar(date(2027, 3, 10))
        base = Reserva.objects.count()
        cancha = Reserva.objects.filter(turno_fijo__isnull=False).first().cancha
        nueva = Reserva.objects.create(
            cancha=cancha, fecha_turno=date(2027, 3, 12), hora_inicio=time(15, 0), hora_fin=time(16, 0),
            usuario=Usuario.objects.get(email='hugo.caceres@demo.talibre.test'),
            creado_por=Usuario.objects.get(email='hugo.caceres@demo.talibre.test'),
            precio_acordado='38000.00', estado=EstadoReserva.CONFIRMADA,
        )

        self._ejecutar(date(2027, 3, 11))

        nueva.refresh_from_db()
        self.assertEqual(nueva.estado, EstadoReserva.CONFIRMADA)
        self.assertEqual(Reserva.objects.count(), base + 1)

    def test_reset_da_de_baja_la_agenda_vieja_y_la_regenera(self):
        self._ejecutar(date(2027, 3, 10))
        esperada = self._agenda_activa()
        anteriores = list(Reserva.objects.values_list('pk', flat=True))
        cancha = Reserva.objects.filter(turno_fijo__isnull=False).first().cancha
        suelta = Reserva.objects.create(
            cancha=cancha, fecha_turno=date(2027, 3, 12), hora_inicio=time(15, 0), hora_fin=time(16, 0),
            usuario=Usuario.objects.get(email='hugo.caceres@demo.talibre.test'),
            creado_por=Usuario.objects.get(email='hugo.caceres@demo.talibre.test'),
            precio_acordado='38000.00', estado=EstadoReserva.CONFIRMADA,
        )

        self._ejecutar(date(2027, 3, 20), '--reset')

        suelta.refresh_from_db()
        self.assertEqual(suelta.estado, EstadoReserva.BAJA)
        self.assertFalse(Reserva.objects.filter(pk__in=anteriores).exclude(estado=EstadoReserva.BAJA).exists())
        self.assertEqual(self._agenda_activa(), esperada)
        self.assertEqual(Usuario.objects.count(), 9)

    def test_reset_repetido_el_mismo_dia_no_deja_la_agenda_vacia(self):
        hoy = date(2027, 3, 10)
        self._ejecutar(hoy)
        esperada = self._agenda_activa()
        self._ejecutar(hoy, '--reset')
        self._ejecutar(hoy, '--reset')
        self.assertEqual(self._agenda_activa(), esperada)

    def test_reset_no_se_combina_con_sin_demo(self):
        with self.assertRaises(CommandError):
            call_command('seed_inicial', '--sin-demo', '--reset', stdout=StringIO())

    def test_actualizar_claves_reemplaza_la_clave_de_las_cuentas_existentes(self):
        self._ejecutar(date(2027, 3, 10))
        self._ejecutar(date(2027, 3, 10))
        usuario = Usuario.objects.get(email='superadmin@demo.talibre.test')
        self.assertTrue(usuario.check_password('ClaveDemoTest2026'))

        with mock.patch.dict(os.environ, {'SEED_PASSWORD_DEMO': 'ClaveNuevaTest2026'}):
            self._ejecutar(date(2027, 3, 10))
            usuario.refresh_from_db()
            self.assertTrue(usuario.check_password('ClaveDemoTest2026'))

            self._ejecutar(date(2027, 3, 10), '--actualizar-claves')
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('ClaveNuevaTest2026'))
        self.assertEqual(Usuario.objects.count(), 9)

    def test_actualizar_claves_no_se_combina_con_sin_demo(self):
        with self.assertRaises(CommandError):
            call_command('seed_inicial', '--sin-demo', '--actualizar-claves', stdout=StringIO())
