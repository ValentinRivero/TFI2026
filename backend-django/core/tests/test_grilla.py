import json
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import (
    AlcanceExcepcion,
    Deporte,
    DiaSemana,
    DuracionTurno,
    EstadoCancha,
    EstadoContrato,
    EstadoReserva,
    EstadoTurnoFijo,
    ExcepcionHoraria,
    HorarioApertura,
    Reserva,
    TipoMotivoExcepcion,
    TipoOcupacion,
    TurnoFijo,
)
from core.services import GrillaService

TOKEN_INVALIDO = 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c3VhcmlvX2lkIjoiMSJ9.firma-invalida'


def _proximo(dia_semana):
    """Próxima fecha futura (de mañana en adelante) que cae en ese día de la semana."""
    manana = timezone.localdate() + timedelta(days=1)
    return manana + timedelta(days=(dia_semana - manana.weekday()) % 7)



@pytest.fixture
def lunes():
    return _proximo(DiaSemana.LUNES)


def _url(complejo, fecha):
    return f'/api/complejos/{complejo.id}/grilla/?fecha={fecha.isoformat()}'


def _abrir(cancha, apertura, cierre, dia=DiaSemana.LUNES, precio=None):
    return HorarioApertura.objects.create(
        cancha=cancha, dia_semana=dia, hora_apertura=apertura, hora_cierre=cierre, precio_diferenciado=precio,
    )


def _grilla(cliente, complejo, fecha):
    respuesta = cliente.get(_url(complejo, fecha))
    assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
    return respuesta.json()


def _bloques(cliente, complejo, fecha, cancha):
    canchas = {item['id']: item for item in _grilla(cliente, complejo, fecha)['canchas']}
    return canchas[cancha.id]['bloques']


def _estados(bloques):
    return {bloque['hora_inicio'][:5]: bloque['estado'] for bloque in bloques}


@pytest.fixture
def cancha(complejo, crear_cancha):
    return crear_cancha(complejo, 'Cancha 1')


@pytest.fixture
def cancha_abierta(cancha):
    """Cancha de 60 minutos abierta los lunes de 13:00 a 18:00."""
    _abrir(cancha, time(13, 0), time(18, 0))
    return cancha


@pytest.fixture
def reservar(jugador):
    def _reservar(cancha, fecha, inicio, fin, estado=EstadoReserva.CONFIRMADA, **campos):
        campos.setdefault('usuario', jugador)
        campos.setdefault('creado_por', jugador)
        return Reserva.objects.create(
            cancha=cancha, fecha_turno=fecha, hora_inicio=inicio, hora_fin=fin,
            precio_acordado=Decimal('38000'), estado=estado, **campos,
        )

    return _reservar


@pytest.fixture
def turno_fijo(dueno):
    def _crear(cancha, inicio, fin, dia=DiaSemana.LUNES, desde=None, hasta=None, **campos):
        campos.setdefault('nombre_cliente_manual', 'Los del Lunes')
        return TurnoFijo.objects.create(
            cancha=cancha, creado_por=dueno, dia_semana=dia, hora_inicio=inicio, hora_fin=fin,
            fecha_inicio_vigencia=desde or timezone.localdate(), fecha_fin_vigencia=hasta, **campos,
        )

    return _crear


@pytest.fixture
def excepcion(dueno):
    def _crear(complejo, fecha, cancha=None, inicio=None, fin=None, hasta=None, **campos):
        campos.setdefault('tipo_motivo', TipoMotivoExcepcion.MANTENIMIENTO)
        alcance = AlcanceExcepcion.DIA_COMPLETO if inicio is None else AlcanceExcepcion.FRANJA_HORARIA
        return ExcepcionHoraria.objects.create(
            complejo=complejo, cancha=cancha, creado_por=dueno, fecha_inicio=fecha, fecha_fin=hasta or fecha,
            es_dia_completo=alcance, hora_inicio=inicio, hora_fin=fin, **campos,
        )

    return _crear


class TestGeneracionDeBloques:
    @pytest.mark.parametrize('duracion, esperados', [
        (60, [('08:00', '09:00'), ('09:00', '10:00'), ('10:00', '11:00'), ('11:00', '12:00')]),
        (90, [('08:00', '09:30'), ('09:30', '11:00')]),
        (120, [('08:00', '10:00'), ('10:00', '12:00')]),
    ])
    def test_divide_el_rango_segun_la_duracion(self, duracion, esperados):
        bloques = GrillaService.generar_bloques(time(8, 0), time(12, 0), duracion)

        assert [(inicio.strftime('%H:%M'), fin.strftime('%H:%M')) for inicio, fin in bloques] == esperados

    def test_un_resto_menor_a_un_turno_no_se_ofrece(self):
        bloques = GrillaService.generar_bloques(time(22, 0), time(23, 59), 60)

        assert bloques == [(time(22, 0), time(23, 0))]

    def test_un_rango_mas_corto_que_el_turno_no_genera_bloques(self):
        assert GrillaService.generar_bloques(time(10, 0), time(11, 0), 90) == []


class TestGrillaPublica:
    def test_es_publica_y_no_pagina(self, cliente, complejo, cancha_abierta, lunes):
        cuerpo = _grilla(cliente, complejo, lunes)

        assert set(cuerpo) == {'complejo', 'fecha', 'dia_semana', 'canchas'}
        assert cuerpo['complejo'] == {'id': complejo.id, 'nombre': complejo.nombre}
        assert cuerpo['fecha'] == lunes.isoformat()
        assert cuerpo['dia_semana'] == DiaSemana.LUNES
        (cancha,) = cuerpo['canchas']
        assert cancha['nombre'] == 'Cancha 1'
        assert cancha['deporte']['nombre'] == 'Fútbol 5'
        assert cancha['duracion_turno_min'] == 60

    def test_ignora_un_token_invalido(self, cliente, complejo, cancha_abierta, lunes):
        cliente.credentials(HTTP_AUTHORIZATION=TOKEN_INVALIDO)

        assert cliente.get(_url(complejo, lunes)).status_code == status.HTTP_200_OK

    def test_genera_bloques_libres_con_el_precio_base(self, cliente, complejo, cancha_abierta, lunes):
        bloques = _bloques(cliente, complejo, lunes, cancha_abierta)

        assert [(b['hora_inicio'], b['hora_fin']) for b in bloques] == [
            ('13:00:00', '14:00:00'), ('14:00:00', '15:00:00'), ('15:00:00', '16:00:00'),
            ('16:00:00', '17:00:00'), ('17:00:00', '18:00:00'),
        ]
        assert {b['precio'] for b in bloques} == {'38000.00'}
        assert {b['estado'] for b in bloques} == {'LIBRE'}
        assert {b['motivo'] for b in bloques} == {None}

    @pytest.mark.parametrize('duracion, inicios', [
        (DuracionTurno.SESENTA, ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00']),
        (DuracionTurno.NOVENTA, ['08:00', '09:30', '11:00', '12:30']),
        (DuracionTurno.CIENTO_VEINTE, ['08:00', '10:00', '12:00']),
    ])
    def test_respeta_la_duracion_del_turno_de_la_cancha(
        self, cliente, complejo, crear_cancha, lunes, duracion, inicios,
    ):
        cancha = crear_cancha(complejo, 'Cancha Variable', duracion_turno_min=duracion)
        _abrir(cancha, time(8, 0), time(14, 0))

        bloques = _bloques(cliente, complejo, lunes, cancha)

        assert [bloque['hora_inicio'][:5] for bloque in bloques] == inicios
        primero = bloques[0]
        assert primero['hora_fin'][:5] == (
            (datetime(2000, 1, 1, 8, 0) + timedelta(minutes=duracion)).strftime('%H:%M')
        )

    def test_recorre_todos_los_rangos_con_cortes(self, cliente, complejo, cancha, lunes):
        _abrir(cancha, time(16, 0), time(19, 0), precio=Decimal('45000'))
        _abrir(cancha, time(8, 0), time(10, 0))

        bloques = _bloques(cliente, complejo, lunes, cancha)

        assert [(b['hora_inicio'][:5], b['precio']) for b in bloques] == [
            ('08:00', '38000.00'), ('09:00', '38000.00'),
            ('16:00', '45000.00'), ('17:00', '45000.00'), ('18:00', '45000.00'),
        ]

    def test_cada_rango_genera_sus_bloques_por_separado(self, cliente, complejo, crear_cancha, lunes):
        cancha = crear_cancha(complejo, 'Pádel 1', 'Pádel', duracion_turno_min=DuracionTurno.NOVENTA)
        _abrir(cancha, time(8, 0), time(12, 0))
        _abrir(cancha, time(16, 0), time(23, 0))

        bloques = _bloques(cliente, complejo, lunes, cancha)

        # 08:00 a 12:00 deja 30 minutos sin turno; el corte no se completa con el rango siguiente.
        assert [bloque['hora_inicio'][:5] for bloque in bloques] == [
            '08:00', '09:30', '16:00', '17:30', '19:00', '20:30',
        ]

    def test_rangos_contiguos_con_precios_distintos(self, cliente, complejo, cancha, lunes):
        _abrir(cancha, time(12, 0), time(14, 0))
        _abrir(cancha, time(14, 0), time(16, 0), precio=Decimal('50000'))

        bloques = _bloques(cliente, complejo, lunes, cancha)

        assert [(b['hora_inicio'][:5], b['precio']) for b in bloques] == [
            ('12:00', '38000.00'), ('13:00', '38000.00'), ('14:00', '50000.00'), ('15:00', '50000.00'),
        ]

    def test_solo_usa_los_horarios_activos_del_dia_de_la_fecha(self, cliente, complejo, cancha, lunes):
        _abrir(cancha, time(8, 0), time(9, 0))
        _abrir(cancha, time(10, 0), time(11, 0), dia=DiaSemana.MARTES)
        _abrir(cancha, time(20, 0), time(21, 0)).desactivar()

        assert _estados(_bloques(cliente, complejo, lunes, cancha)) == {'08:00': 'LIBRE'}
        assert _estados(_bloques(cliente, complejo, lunes + timedelta(days=1), cancha)) == {'10:00': 'LIBRE'}

    def test_cancha_sin_horario_ese_dia_figura_sin_bloques(self, cliente, complejo, cancha, lunes):
        assert _bloques(cliente, complejo, lunes, cancha) == []

    def test_excluye_canchas_en_mantenimiento_dadas_de_baja_o_de_deporte_inactivo(
        self, cliente, complejo, cancha_abierta, crear_cancha, lunes,
    ):
        mantenimiento = crear_cancha(complejo, 'En Arreglo', estado=EstadoCancha.EN_MANTENIMIENTO)
        baja = crear_cancha(complejo, 'Vieja')
        baja.desactivar()
        tenis = crear_cancha(complejo, 'Tenis 1', 'Tenis')
        Deporte.objects.filter(nombre='Tenis').update(estado=0)
        for otra in (mantenimiento, baja, tenis):
            _abrir(otra, time(8, 0), time(12, 0))

        canchas = _grilla(cliente, complejo, lunes)['canchas']

        assert [item['id'] for item in canchas] == [cancha_abierta.id]

    def test_ordena_las_canchas_por_nombre(self, cliente, complejo, crear_cancha, lunes):
        crear_cancha(complejo, 'Cancha B')
        crear_cancha(complejo, 'Cancha A')

        nombres = [item['nombre'] for item in _grilla(cliente, complejo, lunes)['canchas']]

        assert nombres == ['Cancha A', 'Cancha B']

    def test_la_fecha_de_hoy_es_valida(self, cliente, complejo, cancha):
        _abrir(cancha, time(8, 0), time(9, 0), dia=timezone.localdate().weekday())

        assert len(_bloques(cliente, complejo, timezone.localdate(), cancha)) == 1


class TestBloquesYaIniciados:
    """El reloj congelado marca el lunes a las 10:00: el bloque de las 10 ya empezó y no se puede reservar."""

    def test_hoy_los_bloques_libres_ya_iniciados_no_estan_disponibles(self, reloj, cliente, complejo, cancha):
        _abrir(cancha, time(8, 0), time(13, 0))

        assert _estados(_bloques(cliente, complejo, HOY_CONGELADO, cancha)) == {
            '08:00': 'NO_DISPONIBLE', '09:00': 'NO_DISPONIBLE', '10:00': 'NO_DISPONIBLE',
            '11:00': 'LIBRE', '12:00': 'LIBRE',
        }

    def test_un_bloque_iniciado_conserva_su_ocupacion_o_su_cierre(
        self, reloj, cliente, complejo, cancha, reservar, excepcion,
    ):
        _abrir(cancha, time(8, 0), time(11, 0))
        reservar(cancha, HOY_CONGELADO, time(8, 0), time(9, 0))
        excepcion(complejo, HOY_CONGELADO, cancha=cancha, inicio=time(9, 0), fin=time(10, 0))

        estados = _estados(_bloques(cliente, complejo, HOY_CONGELADO, cancha))

        assert estados == {'08:00': 'OCUPADO', '09:00': 'CERRADO_EXCEPCION', '10:00': 'NO_DISPONIBLE'}

    def test_los_dias_siguientes_no_se_ven_afectados(self, reloj, cliente, complejo, cancha):
        _abrir(cancha, time(8, 0), time(10, 0))

        assert set(_estados(_bloques(cliente, complejo, HOY_CONGELADO + timedelta(days=7), cancha)).values()) == {'LIBRE'}

    def test_mas_alla_de_la_anticipacion_maxima_no_se_ofrecen_turnos(
        self, reloj, cliente, complejo, cancha, reservar,
    ):
        # Hoy es el lunes 16/11/2026: se reserva hasta el 16/01/2027.
        _abrir(cancha, time(8, 0), time(10, 0))
        ultimo_lunes, siguiente = HOY_CONGELADO + timedelta(weeks=8), HOY_CONGELADO + timedelta(weeks=9)
        reservar(cancha, siguiente, time(8, 0), time(9, 0))

        assert set(_estados(_bloques(cliente, complejo, ultimo_lunes, cancha)).values()) == {'LIBRE'}
        assert _estados(_bloques(cliente, complejo, siguiente, cancha)) == {'08:00': 'OCUPADO', '09:00': 'NO_DISPONIBLE'}


class TestValidacionesDeGrilla:
    @pytest.mark.parametrize('estado_contrato', [EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA])
    def test_complejo_sin_contrato_activo_responde_404(self, cliente, complejo, cancha_abierta, lunes, estado_contrato):
        complejo.estado_contrato = estado_contrato
        complejo.save()

        assert cliente.get(_url(complejo, lunes)).status_code == status.HTTP_404_NOT_FOUND

    def test_complejo_dado_de_baja_responde_404(self, cliente, complejo, lunes):
        complejo.desactivar()

        assert cliente.get(_url(complejo, lunes)).status_code == status.HTTP_404_NOT_FOUND

    def test_complejo_inexistente_responde_404(self, cliente, rbac, lunes):
        assert cliente.get(f'/api/complejos/999999/grilla/?fecha={lunes.isoformat()}').status_code == 404

    def test_sin_fecha_responde_400(self, cliente, complejo):
        respuesta = cliente.get(f'/api/complejos/{complejo.id}/grilla/')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha' in respuesta.json()['detail']

    @pytest.mark.parametrize('fecha', ['18/11/2026', '2026-13-01', '2026-02-30', 'mañana', ''])
    def test_fecha_con_formato_invalido_responde_400(self, cliente, complejo, fecha):
        respuesta = cliente.get(f'/api/complejos/{complejo.id}/grilla/', {'fecha': fecha})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha' in respuesta.json()['detail']

    def test_fecha_pasada_responde_400(self, cliente, complejo):
        ayer = timezone.localdate() - timedelta(days=1)

        respuesta = cliente.get(_url(complejo, ayer))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha' in respuesta.json()['detail']


class TestExcepcionesEnGrilla:
    def test_una_excepcion_global_de_dia_completo_cierra_todas_las_canchas(
        self, cliente, complejo, cancha_abierta, crear_cancha, excepcion, lunes,
    ):
        otra = crear_cancha(complejo, 'Cancha 2')
        _abrir(otra, time(9, 0), time(11, 0))
        excepcion(complejo, lunes, tipo_motivo=TipoMotivoExcepcion.FERIADO)

        canchas = _grilla(cliente, complejo, lunes)['canchas']

        bloques = [bloque for item in canchas for bloque in item['bloques']]
        assert len(bloques) == 7
        assert {bloque['estado'] for bloque in bloques} == {'CERRADO_EXCEPCION'}
        assert {bloque['motivo'] for bloque in bloques} == {'Feriado'}

    def test_una_franja_de_una_cancha_cierra_solo_los_bloques_superpuestos(
        self, cliente, complejo, cancha_abierta, crear_cancha, excepcion, lunes,
    ):
        otra = crear_cancha(complejo, 'Cancha 2')
        _abrir(otra, time(13, 0), time(18, 0))
        excepcion(complejo, lunes, cancha_abierta, time(14, 30), time(15, 15))

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta)) == {
            '13:00': 'LIBRE', '14:00': 'CERRADO_EXCEPCION', '15:00': 'CERRADO_EXCEPCION',
            '16:00': 'LIBRE', '17:00': 'LIBRE',
        }
        assert set(_estados(_bloques(cliente, complejo, lunes, otra)).values()) == {'LIBRE'}

    def test_una_franja_global_cierra_esa_franja_en_todas_las_canchas(
        self, cliente, complejo, cancha_abierta, crear_cancha, excepcion, lunes,
    ):
        otra = crear_cancha(complejo, 'Cancha 2')
        _abrir(otra, time(13, 0), time(18, 0))
        excepcion(complejo, lunes, None, time(16, 0), time(18, 0), tipo_motivo=TipoMotivoExcepcion.CORTE_SERVICIO)

        for item in (cancha_abierta, otra):
            bloques = _bloques(cliente, complejo, lunes, item)
            assert [b['hora_inicio'][:5] for b in bloques if b['estado'] == 'CERRADO_EXCEPCION'] == ['16:00', '17:00']
            assert {b['motivo'] for b in bloques if b['estado'] == 'CERRADO_EXCEPCION'} == {'Corte de servicio'}

    def test_una_franja_contigua_no_cierra_el_bloque_vecino(self, cliente, complejo, cancha_abierta, excepcion, lunes):
        excepcion(complejo, lunes, cancha_abierta, time(12, 0), time(14, 0))

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['14:00'] == 'LIBRE'
        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['13:00'] == 'CERRADO_EXCEPCION'

    def test_una_excepcion_de_varios_dias_cubre_cada_fecha(self, cliente, complejo, cancha_abierta, excepcion, lunes):
        excepcion(complejo, lunes - timedelta(days=1), hasta=lunes + timedelta(days=1))

        assert set(_estados(_bloques(cliente, complejo, lunes, cancha_abierta)).values()) == {'CERRADO_EXCEPCION'}

    def test_ignora_excepciones_de_otra_fecha_dadas_de_baja_o_de_otro_complejo(
        self, cliente, complejo, complejo_ajeno, cancha_abierta, crear_cancha, excepcion, lunes,
    ):
        excepcion(complejo, lunes + timedelta(days=1))
        excepcion(complejo, lunes, hasta=lunes).desactivar()
        excepcion(complejo_ajeno, lunes)
        excepcion(complejo, lunes, crear_cancha(complejo, 'Cancha 2'))

        assert set(_estados(_bloques(cliente, complejo, lunes, cancha_abierta)).values()) == {'LIBRE'}

    def test_no_expone_la_descripcion(self, cliente, complejo, cancha_abierta, excepcion, lunes):
        excepcion(complejo, lunes, descripcion='Cumpleaños privado de Teodoro Arrúa')

        assert 'Teodoro' not in json.dumps(_grilla(cliente, complejo, lunes))


class TestOcupacionEnGrilla:
    @pytest.mark.parametrize('estado', [
        EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA, EstadoReserva.COMPLETADA,
    ])
    def test_una_reserva_activa_ocupa_el_bloque(self, cliente, complejo, cancha_abierta, reservar, lunes, estado):
        reservar(cancha_abierta, lunes, time(15, 0), time(16, 0), estado=estado)

        estados = _estados(_bloques(cliente, complejo, lunes, cancha_abierta))

        assert estados['15:00'] == 'OCUPADO'
        assert [hora for hora, valor in estados.items() if valor == 'OCUPADO'] == ['15:00']

    @pytest.mark.parametrize('estado', [
        EstadoReserva.BAJA, EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE,
    ])
    def test_una_reserva_no_ocupante_deja_el_bloque_libre(
        self, cliente, complejo, cancha_abierta, reservar, lunes, estado,
    ):
        reservar(cancha_abierta, lunes, time(15, 0), time(16, 0), estado=estado)

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['15:00'] == 'LIBRE'

    def test_una_reserva_que_abarca_dos_bloques_ocupa_ambos(self, cliente, complejo, cancha_abierta, reservar, lunes):
        reservar(cancha_abierta, lunes, time(14, 30), time(16, 0))

        estados = _estados(_bloques(cliente, complejo, lunes, cancha_abierta))

        assert (estados['14:00'], estados['15:00'], estados['16:00']) == ('OCUPADO', 'OCUPADO', 'LIBRE')

    def test_ignora_reservas_de_otra_fecha_o_de_otra_cancha(
        self, cliente, complejo, cancha_abierta, crear_cancha, reservar, lunes,
    ):
        reservar(cancha_abierta, lunes + timedelta(days=7), time(15, 0), time(16, 0))
        reservar(crear_cancha(complejo, 'Cancha 2'), lunes, time(15, 0), time(16, 0))

        assert set(_estados(_bloques(cliente, complejo, lunes, cancha_abierta)).values()) == {'LIBRE'}

    def test_la_reserva_prevalece_sobre_la_excepcion(
        self, cliente, complejo, cancha_abierta, reservar, excepcion, lunes,
    ):
        reservar(cancha_abierta, lunes, time(15, 0), time(16, 0))
        excepcion(complejo, lunes, tipo_motivo=TipoMotivoExcepcion.CLIMA)

        bloques = {b['hora_inicio'][:5]: b for b in _bloques(cliente, complejo, lunes, cancha_abierta)}

        assert (bloques['15:00']['estado'], bloques['15:00']['motivo']) == ('OCUPADO', None)
        assert (bloques['16:00']['estado'], bloques['16:00']['motivo']) == ('CERRADO_EXCEPCION', 'Condiciones climáticas')

    def test_un_turno_fijo_vigente_ocupa_su_horario(self, cliente, complejo, cancha_abierta, turno_fijo, lunes):
        turno_fijo(cancha_abierta, time(17, 0), time(18, 0))

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'OCUPADO'

    def test_un_turno_fijo_ocupa_dentro_de_su_vigencia(self, cliente, complejo, cancha_abierta, turno_fijo, lunes):
        turno_fijo(cancha_abierta, time(17, 0), time(18, 0), desde=lunes, hasta=lunes)

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'OCUPADO'

    @pytest.mark.parametrize('desde_dias, hasta_dias', [(1, None), (-14, -1)])
    def test_un_turno_fijo_fuera_de_vigencia_no_ocupa(
        self, cliente, complejo, cancha_abierta, turno_fijo, lunes, desde_dias, hasta_dias,
    ):
        hasta = lunes + timedelta(days=hasta_dias) if hasta_dias is not None else None
        turno_fijo(cancha_abierta, time(17, 0), time(18, 0), desde=lunes + timedelta(days=desde_dias), hasta=hasta)

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'LIBRE'

    @pytest.mark.parametrize('estado', [EstadoTurnoFijo.PAUSADO, EstadoTurnoFijo.BAJA])
    def test_un_turno_fijo_pausado_o_dado_de_baja_no_ocupa(
        self, cliente, complejo, cancha_abierta, turno_fijo, lunes, estado,
    ):
        turno_fijo(cancha_abierta, time(17, 0), time(18, 0), estado=estado)

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'LIBRE'

    def test_un_turno_fijo_de_otro_dia_no_ocupa(self, cliente, complejo, cancha_abierta, turno_fijo, lunes):
        turno_fijo(cancha_abierta, time(17, 0), time(18, 0), dia=DiaSemana.MARTES)

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'LIBRE'

    def test_cancelar_la_fecha_de_un_turno_fijo_libera_el_bloque(
        self, cliente, dueno, complejo, cancha_abierta, turno_fijo, reservar, lunes,
    ):
        turno = turno_fijo(cancha_abierta, time(17, 0), time(18, 0))
        reservar(
            cancha_abierta, lunes, time(17, 0), time(18, 0), estado=EstadoReserva.CANCELADA_COMPLEJO,
            usuario=None, creado_por=dueno, turno_fijo=turno, nombre_cliente_manual='Los del Lunes',
            tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
        )

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'LIBRE'
        assert _estados(_bloques(cliente, complejo, lunes + timedelta(days=7), cancha_abierta))['17:00'] == 'OCUPADO'

    def test_la_reserva_generada_por_el_turno_fijo_lo_mantiene_ocupado(
        self, cliente, dueno, complejo, cancha_abierta, turno_fijo, reservar, lunes,
    ):
        turno = turno_fijo(cancha_abierta, time(17, 0), time(18, 0))
        reservar(
            cancha_abierta, lunes, time(17, 0), time(18, 0), usuario=None, creado_por=dueno, turno_fijo=turno,
            nombre_cliente_manual='Los del Lunes', tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
        )

        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['17:00'] == 'OCUPADO'

    def test_el_turno_fijo_prevalece_sobre_la_excepcion(
        self, cliente, complejo, cancha_abierta, turno_fijo, excepcion, lunes,
    ):
        turno_fijo(cancha_abierta, time(13, 0), time(14, 0))
        excepcion(complejo, lunes)

        estados = _estados(_bloques(cliente, complejo, lunes, cancha_abierta))

        assert estados['13:00'] == 'OCUPADO'
        assert estados['14:00'] == 'CERRADO_EXCEPCION'


CLAVES_GRILLA = {'complejo', 'fecha', 'dia_semana', 'canchas'}
CLAVES_CANCHA = {'id', 'nombre', 'deporte', 'duracion_turno_min', 'bloques'}
CLAVES_BLOQUE = {'hora_inicio', 'hora_fin', 'precio', 'estado', 'motivo'}


class TestPrivacidadDeGrilla:
    def test_no_expone_datos_de_clientes_ni_de_jugadores(
        self, cliente, jugador, dueno, complejo, cancha_abierta, reservar, turno_fijo, lunes,
    ):
        jugador.telefono = '3777 000123'
        jugador.save()
        reservar(cancha_abierta, lunes, time(13, 0), time(14, 0), observaciones='Trae pelota')
        reservar(
            cancha_abierta, lunes, time(14, 0), time(15, 0), usuario=None, creado_por=dueno,
            nombre_cliente_manual='Fermina Ledesma', telefono_cliente_manual='3777 000456',
            tipo_ocupacion=TipoOcupacion.MANUAL,
        )
        turno_fijo(
            cancha_abierta, time(16, 0), time(17, 0),
            nombre_cliente_manual='Peña de los Jueves', telefono_cliente_manual='3777 000789',
        )

        cuerpo = _grilla(cliente, complejo, lunes)
        texto = json.dumps(cuerpo, ensure_ascii=False)

        for dato in (
            'Jugador Prueba', 'jugador@talibre.test', '3777 000123', 'Trae pelota', 'Fermina', '3777 000456',
            'Peña de los Jueves', '3777 000789', 'Dueño Prueba', 'dueno@talibre.test',
        ):
            assert dato not in texto
        assert set(cuerpo) == CLAVES_GRILLA
        (item,) = cuerpo['canchas']
        assert set(item) == CLAVES_CANCHA
        assert all(set(bloque) == CLAVES_BLOQUE for bloque in item['bloques'])
        assert [b['estado'] for b in item['bloques']] == ['OCUPADO', 'OCUPADO', 'LIBRE', 'OCUPADO', 'LIBRE']


class TestRendimientoDeGrilla:
    def _consultas(self, cliente, complejo, fecha):
        """Mide el cálculo desde la base: se descarta la caché antes de pedir la grilla."""
        cache.clear()
        with CaptureQueriesContext(connection) as contexto:
            _grilla(cliente, complejo, fecha)
        return len(contexto.captured_queries)

    def test_la_cantidad_de_consultas_no_crece_con_canchas_ni_ocupaciones(
        self, cliente, complejo, crear_cancha, reservar, turno_fijo, excepcion, lunes,
    ):
        primera = crear_cancha(complejo, 'Cancha 1')
        _abrir(primera, time(8, 0), time(23, 0))
        base = self._consultas(cliente, complejo, lunes)

        for numero in range(2, 7):
            otra = crear_cancha(complejo, f'Cancha {numero}')
            _abrir(otra, time(8, 0), time(12, 0))
            _abrir(otra, time(16, 0), time(23, 0))
            reservar(otra, lunes, time(9, 0), time(10, 0))
            turno_fijo(otra, time(20, 0), time(21, 0))
            excepcion(complejo, lunes, otra, time(17, 0), time(18, 0))

        assert self._consultas(cliente, complejo, lunes) == base
        assert base <= 6


class TestCacheDeGrilla:
    def _consultas(self, cliente, complejo, fecha):
        with CaptureQueriesContext(connection) as contexto:
            cuerpo = _grilla(cliente, complejo, fecha)
        return len(contexto.captured_queries), cuerpo

    def test_la_segunda_consulta_sale_de_la_cache(self, cliente, complejo, cancha_abierta, lunes):
        primera, cuerpo_1 = self._consultas(cliente, complejo, lunes)
        segunda, cuerpo_2 = self._consultas(cliente, complejo, lunes)

        assert primera > 0
        assert segunda == 0
        assert cuerpo_1 == cuerpo_2

    def test_una_reserva_confirmada_invalida_la_cache(
        self, cliente, jugador, cliente_de, complejo, cancha_abierta, lunes, django_capture_on_commit_callbacks,
    ):
        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['14:00'] == 'LIBRE'

        with django_capture_on_commit_callbacks(execute=True):
            respuesta = cliente_de(jugador).post('/api/reservas/', {
                'cancha': cancha_abierta.id, 'fecha_turno': lunes.isoformat(), 'hora_inicio': '14:00',
            }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert _estados(_bloques(cliente, complejo, lunes, cancha_abierta))['14:00'] == 'OCUPADO'

    def test_suspender_el_contrato_invalida_la_cache(
        self, cliente, superadmin, cliente_de, complejo, cancha_abierta, lunes, django_capture_on_commit_callbacks,
    ):
        _grilla(cliente, complejo, lunes)

        with django_capture_on_commit_callbacks(execute=True):
            cliente_de(superadmin).patch(
                f'/api/contratos/{complejo.id}/', {'estado_contrato': EstadoContrato.SUSPENDIDO}, format='json',
            )

        assert cliente.get(_url(complejo, lunes)).status_code == status.HTTP_404_NOT_FOUND

    def test_cada_fecha_y_cada_complejo_tienen_su_propia_entrada(
        self, cliente, complejo, complejo_ajeno, cancha_abierta, crear_cancha, lunes,
    ):
        _abrir(crear_cancha(complejo_ajeno, 'Ajena'), time(13, 0), time(18, 0))
        _grilla(cliente, complejo, lunes)

        otra_fecha, _ = self._consultas(cliente, complejo, lunes + timedelta(days=7))
        otro_complejo, cuerpo = self._consultas(cliente, complejo_ajeno, lunes)

        assert otra_fecha > 0 and otro_complejo > 0
        assert cuerpo['complejo']['id'] == complejo_ajeno.id

    def test_las_marcas_del_reloj_se_recalculan_sobre_la_cache(self, reloj, cliente, complejo, cancha):
        _abrir(cancha, time(8, 0), time(13, 0))
        assert _estados(_bloques(cliente, complejo, HOY_CONGELADO, cancha))['11:00'] == 'LIBRE'

        reloj.return_value = reloj.return_value.replace(hour=11, minute=30)
        cantidad, cuerpo = self._consultas(cliente, complejo, HOY_CONGELADO)

        assert cantidad == 0
        assert _estados(cuerpo['canchas'][0]['bloques'])['11:00'] == 'NO_DISPONIBLE'
        assert _estados(cuerpo['canchas'][0]['bloques'])['12:00'] == 'LIBRE'

    def test_se_guarda_con_un_tiempo_de_vida_corto(self, cliente, complejo, cancha_abierta, lunes, settings):
        settings.GRILLA_CACHE_SEGUNDOS = 45

        with mock.patch('core.services.cache.set', wraps=cache.set) as guardar:
            _grilla(cliente, complejo, lunes)

        ((clave, _, tiempo_de_vida), _) = guardar.call_args
        assert clave.startswith(f'grilla:{complejo.id}:{lunes.isoformat()}:v')
        assert tiempo_de_vida == 45

    def test_si_la_cache_falla_la_grilla_se_calcula_igual(self, cliente, complejo, cancha_abierta, lunes):
        caida = mock.MagicMock()
        caida.add.side_effect = caida.get.side_effect = ConnectionError('Redis no responde')
        with mock.patch('core.services.cache', caida):
            respuesta = cliente.get(_url(complejo, lunes))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['canchas'][0]['bloques']

    def test_si_falla_guardar_o_invalidar_no_se_rompe_nada(
        self, cliente, complejo, cancha_abierta, lunes,
    ):
        from core.services import CacheGrillaService

        caida = mock.MagicMock()
        caida.get.return_value = None
        caida.set.side_effect = caida.incr.side_effect = ConnectionError('Redis no responde')
        with mock.patch('core.services.cache', caida):
            assert cliente.get(_url(complejo, lunes)).status_code == status.HTTP_200_OK
            CacheGrillaService.invalidar(complejo.id)
        caida.incr.assert_called_once()


class TestLimiteDeLaGrilla:
    def test_tiene_un_limite_propio_mas_amplio_que_el_anonimo(self, cliente, complejo, cancha_abierta, lunes):
        for _ in range(61):
            assert cliente.get(_url(complejo, lunes)).status_code == status.HTTP_200_OK

        assert cliente.get('/api/complejos/').status_code == status.HTTP_200_OK

    def test_al_superarlo_responde_429(self, cliente, complejo, cancha_abierta, lunes):
        from core.throttles import GrillaRateThrottle

        with mock.patch.object(GrillaRateThrottle, 'get_rate', return_value='2/minute'):
            codigos = [cliente.get(_url(complejo, lunes)).status_code for _ in range(3)]

        assert codigos == [200, 200, 429]
