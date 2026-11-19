"""
Concurrencia real del motor de reservas: hilos con conexiones propias que compiten por la misma cancha.
Solo tiene sentido sobre PostgreSQL (SQLite ignora select_for_update); en CI corre con
config.settings_concurrencia contra un servicio de PostgreSQL descartable.
"""
import threading
from datetime import time, timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.db import connection, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.exceptions import ConflictoNegocio
from core.models import (
    Cancha,
    Cobertura,
    Complejo,
    Deporte,
    EstadoContrato,
    HorarioApertura,
    Iluminacion,
    Reserva,
    Rol,
    TipoSuperficie,
    TurnoFijo,
    Usuario,
)
from core.repositories import ESTADOS_RESERVA_OCUPANTES
from core.services import ReservaService, TurnoFijoService

HILOS = 8
PASSWORD = 'CanchaLibre#2026'


class ConcurrenciaDeReservasTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor == 'sqlite':
            self.skipTest('SQLite no bloquea filas con select_for_update: esta prueba corre sobre PostgreSQL.')
        call_command('seed_inicial', '--sin-demo', stdout=StringIO())
        dueno = Usuario.objects.create_user(
            email='dueno.concurrencia@talibre.test', password=PASSWORD,
            rol=Rol.objects.get(nombre='DUENO_COMPLEJO'), nombre_completo='Dueño Concurrencia',
        )
        self.dueno = dueno
        complejo = Complejo.objects.create(
            propietario=dueno, nombre='Complejo Concurrencia', direccion='Calle Los Ceibos 200, Goya',
            latitud=Decimal('-29.140000'), longitud=Decimal('-59.260000'), estado_contrato=EstadoContrato.ACTIVO,
        )
        self.cancha = Cancha.objects.create(
            complejo=complejo, nombre='Cancha 1', deporte=Deporte.objects.get(nombre='Fútbol 5'),
            tipo_superficie=TipoSuperficie.CESPED_SINTETICO, cobertura=Cobertura.DESCUBIERTA,
            iluminacion=Iluminacion.LED, precio_base=Decimal('38000.00'),
        )
        self.fecha = timezone.localdate() + timedelta(days=7)
        HorarioApertura.objects.create(
            cancha=self.cancha, dia_semana=self.fecha.weekday(), hora_apertura=time(14, 0), hora_cierre=time(23, 0),
        )
        jugador = Rol.objects.get(nombre='JUGADOR')
        self.jugadores = [
            Usuario.objects.create_user(
                email=f'jugador{numero}@talibre.test', password=PASSWORD, rol=jugador,
                nombre_completo=f'Jugador {numero}',
            )
            for numero in range(HILOS)
        ]

    def _en_paralelo(self, tareas):
        """Arranca todas las tareas a la vez (barrera) y devuelve, por tarea, ('ok', valor), ('409', ...) o ('error', ...)."""
        barrera = threading.Barrier(len(tareas))
        resultados = [None] * len(tareas)

        def correr(indice, tarea):
            try:
                barrera.wait(timeout=30)
                resultados[indice] = ('ok', tarea())
            except ConflictoNegocio as error:
                resultados[indice] = ('409', str(error.detail))
            except Exception as error:  # noqa: BLE001 - cualquier otra falla debe hacer fallar la prueba
                resultados[indice] = ('error', repr(error))
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=correr, args=(indice, tarea)) for indice, tarea in enumerate(tareas)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=60)
        self.assertFalse(any(hilo.is_alive() for hilo in hilos), 'Un hilo quedó bloqueado: posible deadlock.')
        return resultados

    def _datos_reserva(self):
        return {'cancha': self.cancha, 'fecha_turno': self.fecha, 'hora_inicio': time(20, 0)}

    def _datos_turno_fijo(self, nombre):
        return {
            'cancha': self.cancha, 'dia_semana': self.fecha.weekday(), 'hora_inicio': time(20, 0),
            'fecha_inicio_vigencia': timezone.localdate(), 'fecha_fin_vigencia': self.fecha,
            'nombre_cliente_manual': nombre, 'telefono_cliente_manual': '3777 000777',
        }

    def _contar(self, resultados):
        tipos = [tipo for tipo, _ in resultados]
        errores = [detalle for tipo, detalle in resultados if tipo == 'error']
        self.assertEqual(errores, [])
        return tipos.count('ok'), tipos.count('409')

    def test_solo_una_reserva_simultanea_del_mismo_turno_se_confirma(self):
        tareas = [
            lambda usuario=usuario: ReservaService.crear_reserva(self._datos_reserva(), usuario, None)
            for usuario in self.jugadores
        ]

        exitos, conflictos = self._contar(self._en_paralelo(tareas))

        self.assertEqual((exitos, conflictos), (1, HILOS - 1))
        ocupantes = Reserva.objects.filter(cancha=self.cancha, estado__in=ESTADOS_RESERVA_OCUPANTES)
        self.assertEqual(ocupantes.count(), 1)

    def test_por_la_api_una_responde_201_y_el_resto_409(self):
        from core.serializers_auth import TokenConRolSerializer

        tokens = [str(TokenConRolSerializer.get_token(usuario).access_token) for usuario in self.jugadores]
        cuerpo = {'cancha': self.cancha.id, 'fecha_turno': self.fecha.isoformat(), 'hora_inicio': '20:00'}

        def pedir(token):
            api = APIClient()
            api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            return api.post('/api/reservas/', cuerpo, format='json').status_code

        resultados = self._en_paralelo([lambda token=token: pedir(token) for token in tokens])
        codigos = sorted(valor for tipo, valor in resultados if tipo == 'ok')

        self.assertEqual(codigos, [201] + [409] * (HILOS - 1))
        self.assertEqual(Reserva.objects.count(), 1)

    def test_una_reserva_y_un_turno_fijo_simultaneos_no_se_pisan(self):
        # Ninguna restricción de base cruza reservas con turnos fijos: solo el bloqueo de la cancha lo impide.
        mitad = HILOS // 2
        tareas = [
            lambda usuario=usuario: ReservaService.crear_reserva(self._datos_reserva(), usuario, None)
            for usuario in self.jugadores[:mitad]
        ] + [
            lambda numero=numero: TurnoFijoService.crear(self._datos_turno_fijo(f'Equipo {numero}'), self.dueno)
            for numero in range(HILOS - mitad)
        ]

        exitos, conflictos = self._contar(self._en_paralelo(tareas))

        self.assertEqual((exitos, conflictos), (1, HILOS - 1))
        reservas = Reserva.objects.filter(estado__in=ESTADOS_RESERVA_OCUPANTES).count()
        self.assertEqual(reservas + TurnoFijo.objects.count(), 1)

    def test_dos_turnos_fijos_simultaneos_del_mismo_horario(self):
        tareas = [
            lambda numero=numero: TurnoFijoService.crear(self._datos_turno_fijo(f'Equipo {numero}'), self.dueno)
            for numero in range(HILOS)
        ]

        exitos, conflictos = self._contar(self._en_paralelo(tareas))

        self.assertEqual((exitos, conflictos), (1, HILOS - 1))
        self.assertEqual(TurnoFijo.objects.count(), 1)

    def test_reservas_de_canchas_distintas_no_se_esperan_entre_si(self):
        otra = Cancha.objects.create(
            complejo=self.cancha.complejo, nombre='Cancha 2', deporte=self.cancha.deporte,
            tipo_superficie=TipoSuperficie.CESPED_SINTETICO, cobertura=Cobertura.DESCUBIERTA,
            iluminacion=Iluminacion.LED, precio_base=Decimal('38000.00'),
        )
        HorarioApertura.objects.create(
            cancha=otra, dia_semana=self.fecha.weekday(), hora_apertura=time(14, 0), hora_cierre=time(23, 0),
        )
        canchas = [self.cancha, otra]
        tareas = [
            lambda indice=indice: ReservaService.crear_reserva(
                {'cancha': canchas[indice % 2], 'fecha_turno': self.fecha, 'hora_inicio': time(14 + indice // 2, 0)},
                self.jugadores[indice], None,
            )
            for indice in range(HILOS)
        ]

        exitos, conflictos = self._contar(self._en_paralelo(tareas))

        self.assertEqual((exitos, conflictos), (HILOS, 0))
