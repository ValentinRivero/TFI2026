from datetime import date, time
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    Cancha,
    Cobertura,
    Complejo,
    Deporte,
    DiaSemana,
    EstadoReserva,
    HorarioApertura,
    Iluminacion,
    Reserva,
    Rol,
    TipoSuperficie,
    TurnoFijo,
    Usuario,
)


class RestriccionesHorariasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre='DUENO_COMPLEJO')
        cls.dueno = Usuario.objects.create_user(
            email='dueno@talibre.test', password='ClaveSegura123', rol=rol, nombre_completo='Dueño Test',
        )
        complejo = Complejo.objects.create(
            propietario=cls.dueno,
            nombre='Complejo Test',
            direccion='Calle 1, Goya',
            latitud=Decimal('-29.146820'),
            longitud=Decimal('-59.271430'),
        )
        cls.cancha = Cancha.objects.create(
            complejo=complejo,
            deporte=Deporte.objects.create(nombre='Fútbol 5'),
            nombre='Cancha 1',
            tipo_superficie=TipoSuperficie.CESPED_SINTETICO,
            cobertura=Cobertura.DESCUBIERTA,
            iluminacion=Iluminacion.LED,
            precio_base=Decimal('38000.00'),
        )

    def _reserva(self, **campos):
        datos = {
            'cancha': self.cancha,
            'usuario': self.dueno,
            'creado_por': self.dueno,
            'fecha_turno': date(2026, 12, 1),
            'hora_inicio': time(20, 0),
            'hora_fin': time(21, 0),
            'precio_acordado': Decimal('38000.00'),
            'estado': EstadoReserva.CONFIRMADA,
        }
        datos.update(campos)
        return Reserva.objects.create(**datos)

    def test_reserva_rechaza_fin_igual_o_anterior_al_inicio(self):
        for hora_fin in (time(20, 0), time(19, 0)):
            with self.subTest(hora_fin=hora_fin), self.assertRaises(IntegrityError), transaction.atomic():
                self._reserva(hora_fin=hora_fin)

    def test_turno_fijo_rechaza_fin_igual_o_anterior_al_inicio(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TurnoFijo.objects.create(
                cancha=self.cancha,
                usuario=self.dueno,
                creado_por=self.dueno,
                dia_semana=DiaSemana.MARTES,
                hora_inicio=time(21, 0),
                hora_fin=time(21, 0),
                fecha_inicio_vigencia=date(2026, 11, 17),
            )

    def test_horario_rechaza_cierre_igual_o_anterior_a_la_apertura(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            HorarioApertura.objects.create(
                cancha=self.cancha,
                dia_semana=DiaSemana.LUNES,
                hora_apertura=time(23, 0),
                hora_cierre=time(14, 0),
            )

    def test_rechaza_dos_reservas_activas_en_el_mismo_turno(self):
        self._reserva()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._reserva(estado=EstadoReserva.PENDIENTE)

    def test_permite_reservar_un_turno_cancelado(self):
        self._reserva(estado=EstadoReserva.CANCELADA_JUGADOR)
        nueva = self._reserva()
        self.assertEqual(
            Reserva.objects.filter(cancha=self.cancha, fecha_turno=nueva.fecha_turno, hora_inicio=nueva.hora_inicio).count(),
            2,
        )
