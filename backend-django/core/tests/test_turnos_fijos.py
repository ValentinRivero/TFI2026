from datetime import date, time, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.exceptions import NotFound

from conftest import HOY_CONGELADO
from core.models import (
    DiaSemana,
    DuracionTurno,
    EstadoCancha,
    EstadoContrato,
    EstadoReserva,
    EstadoTurnoFijo,
    LogAuditoria,
    Reserva,
    RolPermiso,
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
    TipoOcupacion,
    TurnoFijo,
)
from core.services import DifusionGrillaService, TurnoFijoService

URL = '/api/turnos-fijos/'
URL_RESERVAS = '/api/reservas/'

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)


def _martes(semanas):
    return MARTES + timedelta(days=7 * semanas)


def _url(turno, accion=''):
    return f'{URL}{turno.id}/{accion}'


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    """Cancha de 60 minutos abierta los martes de 14 a 18 al precio base y de 18 a 23 a precio diferenciado."""
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(18, 0))
    crear_horario(cancha, DiaSemana.MARTES, time(18, 0), time(23, 0), precio=Decimal('45000.00'))
    return cancha


@pytest.fixture
def cancha_ajena(complejo_ajeno, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo_ajeno, 'Cancha Ajena')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


def _alta(cancha, hora='21:00', desde=MARTES, hasta=None, dia=DiaSemana.MARTES, **extra):
    datos = {
        'cancha': cancha.id,
        'dia_semana': dia,
        'hora_inicio': hora,
        'fecha_inicio_vigencia': desde.isoformat(),
        'fecha_fin_vigencia': hasta.isoformat() if hasta else None,
        'nombre_cliente_manual': 'Los del Martes',
        'telefono_cliente_manual': '3777 000401',
    }
    datos.update(extra)
    return datos


@pytest.fixture
def registrar(reloj, dueno, cliente_de):
    def _registrar(cancha, usuario=None, **cambios):
        return cliente_de(usuario or dueno).post(URL, _alta(cancha, **cambios), format='json')

    return _registrar


@pytest.fixture
def turno(crear_turno_fijo, cancha):
    """Turno fijo de los martes de 21 a 22, vigente desde mañana y sin fecha de fin."""
    return crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES)


def _ids(respuesta):
    return [turno['id'] for turno in respuesta.json()['results']]


class TestConsultaDeTurnosFijos:
    def test_lista_los_de_una_cancha_paginados_con_el_contacto(self, reloj, operador, cliente_de, cancha, turno):
        respuesta = cliente_de(operador).get(URL, {'cancha': cancha.id})

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert set(cuerpo) == {'count', 'next', 'previous', 'results'}
        (item,) = cuerpo['results']
        assert item['id'] == turno.id
        assert item['dia_semana_nombre'] == 'Martes'
        assert (item['hora_inicio'], item['hora_fin']) == ('21:00:00', '22:00:00')
        assert item['cliente'] == {'nombre': 'Los del Martes', 'telefono': '3777 000401', 'email': None}
        assert item['estado_nombre'] == 'Vigente'
        assert 'creado_por' not in item

    def test_un_turno_de_un_jugador_registrado_muestra_su_contacto(
        self, reloj, dueno, jugador, crear_turno_fijo, cliente_de, cancha,
    ):
        crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(20, 0), time(21, 0), desde=MARTES, usuario=jugador,
            nombre_cliente_manual='', telefono_cliente_manual='',
        )

        (item,) = cliente_de(dueno).get(URL).json()['results']

        assert item['cliente']['email'] == 'jugador@talibre.test'

    def test_filtra_por_fecha_dia_y_estado(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha, turno):
        pausado = crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(15, 0), time(16, 0), desde=MARTES, estado=EstadoTurnoFijo.PAUSADO,
        )
        miercoles = crear_turno_fijo(cancha, DiaSemana.MIERCOLES, time(15, 0), time(16, 0), desde=MARTES)
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(16, 0), time(17, 0), desde=_martes(4))

        api = cliente_de(dueno)

        assert set(_ids(api.get(URL, {'fecha': _martes(1).isoformat()}))) == {turno.id, pausado.id}
        assert _ids(api.get(URL, {'dia_semana': DiaSemana.MIERCOLES})) == [miercoles.id]
        assert _ids(api.get(URL, {'estado': EstadoTurnoFijo.PAUSADO})) == [pausado.id]

    def test_excluye_los_dados_de_baja(self, reloj, dueno, cliente_de, turno):
        turno.desactivar()

        assert cliente_de(dueno).get(URL).json()['count'] == 0

    def test_pagina_de_a_20(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        for semana in range(21):
            crear_turno_fijo(cancha, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=_martes(semana), hasta=_martes(semana))

        cuerpo = cliente_de(dueno).get(URL).json()

        assert cuerpo['count'] == 21 and len(cuerpo['results']) == 20

    def test_lo_ajeno_responde_404(self, reloj, dueno, crear_turno_fijo, cliente_de, complejo_ajeno, cancha_ajena):
        ajeno = crear_turno_fijo(cancha_ajena, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=MARTES)
        api = cliente_de(dueno)

        assert api.get(URL, {'cancha': cancha_ajena.id}).status_code == status.HTTP_404_NOT_FOUND
        assert api.get(URL, {'complejo': complejo_ajeno.id}).status_code == status.HTTP_404_NOT_FOUND
        assert api.get(_url(ajeno)).status_code == status.HTTP_404_NOT_FOUND
        assert api.get(URL).json()['count'] == 0

    def test_el_superadmin_ve_los_de_cualquier_complejo(self, reloj, superadmin, crear_turno_fijo, cliente_de, cancha_ajena):
        crear_turno_fijo(cancha_ajena, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=MARTES)

        assert cliente_de(superadmin).get(URL).json()['count'] == 1

    def test_el_jugador_recibe_403(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN


class TestAltaDeTurnosFijos:
    def test_registra_un_turno_fijo_vigente(self, registrar, dueno, cancha):
        respuesta = registrar(cancha, hasta=_martes(4))

        assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.json()
        cuerpo = respuesta.json()
        assert (cuerpo['hora_inicio'], cuerpo['hora_fin']) == ('21:00:00', '22:00:00')
        assert cuerpo['estado'] == EstadoTurnoFijo.VIGENTE
        assert cuerpo['fecha_fin_vigencia'] == _martes(4).isoformat()
        turno = TurnoFijo.objects.get()
        assert turno.creado_por == dueno and turno.usuario is None

    def test_sin_fecha_de_fin_queda_por_tiempo_indefinido(self, registrar, cancha):
        assert registrar(cancha).json()['fecha_fin_vigencia'] is None

    def test_siempre_nace_vigente(self, registrar, cancha):
        assert registrar(cancha, estado=EstadoTurnoFijo.PAUSADO).json()['estado'] == EstadoTurnoFijo.VIGENTE

    @pytest.mark.parametrize('duracion, fin', [(DuracionTurno.NOVENTA, '15:30:00'), (DuracionTurno.CIENTO_VEINTE, '16:00:00')])
    def test_calcula_hora_fin_con_la_duracion_de_la_cancha(
        self, registrar, complejo, crear_cancha, crear_horario, duracion, fin,
    ):
        cancha = crear_cancha(complejo, 'Cancha Larga', duracion_turno_min=duracion)
        crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(20, 0))

        assert registrar(cancha, hora='14:00', hora_fin='23:00').json()['hora_fin'] == fin

    @pytest.mark.parametrize('hora, dia', [
        ('21:30', DiaSemana.MARTES), ('23:00', DiaSemana.MARTES), ('21:00', DiaSemana.MIERCOLES),
    ])
    def test_un_horario_fuera_de_la_grilla_responde_400(self, registrar, cancha, hora, dia):
        respuesta = registrar(cancha, hora=hora, dia=dia, desde=MARTES)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_inicio' in respuesta.json()['detail']

    def test_no_empieza_en_el_pasado(self, registrar, cancha):
        respuesta = registrar(cancha, desde=HOY - timedelta(days=6))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_inicio_vigencia' in respuesta.json()['detail']

    def test_el_fin_no_puede_ser_anterior_al_inicio(self, registrar, cancha):
        respuesta = registrar(cancha, desde=_martes(2), hasta=_martes(1))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_fin_vigencia' in respuesta.json()['detail']

    def test_la_vigencia_debe_incluir_ese_dia_de_la_semana(self, registrar, cancha):
        respuesta = registrar(cancha, desde=MARTES + timedelta(days=1), hasta=MARTES + timedelta(days=5))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail']['fecha_fin_vigencia'] == 'La vigencia no incluye ningún martes.'

    def test_una_cancha_en_mantenimiento_no_admite_turnos_fijos(self, registrar, cancha):
        cancha.estado = EstadoCancha.EN_MANTENIMIENTO
        cancha.save()

        assert registrar(cancha).status_code == status.HTTP_400_BAD_REQUEST

    def test_un_complejo_suspendido_no_admite_turnos_fijos(self, registrar, complejo, cancha):
        complejo.estado_contrato = EstadoContrato.SUSPENDIDO
        complejo.save()

        assert registrar(cancha).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize('cambios, campo', [
        ({'nombre_cliente_manual': ''}, 'nombre_cliente_manual'),
        ({'telefono_cliente_manual': 'sin telefono'}, 'telefono_cliente_manual'),
        ({'dia_semana': 7}, 'dia_semana'),
        ({'fecha_inicio_vigencia': '17/11/2026'}, 'fecha_inicio_vigencia'),
    ])
    def test_valida_los_datos(self, registrar, cancha, cambios, campo):
        respuesta = registrar(cancha, **cambios)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_sanitiza_el_nombre_del_cliente(self, registrar, cancha):
        registrar(cancha, nombre_cliente_manual='<script>x</script>Los <i>del</i> Martes')

        assert TurnoFijo.objects.get().nombre_cliente_manual == 'Los del Martes'

    def test_una_cancha_de_otro_complejo_responde_403(self, registrar, cancha_ajena):
        assert registrar(cancha_ajena).status_code == status.HTTP_403_FORBIDDEN
        assert not TurnoFijo.objects.exists()

    def test_el_operador_registra_en_su_complejo(self, registrar, operador, cancha):
        assert registrar(cancha, usuario=operador).status_code == status.HTTP_201_CREATED

    def test_el_superadmin_registra_en_cualquier_complejo(self, registrar, superadmin, cancha_ajena):
        assert registrar(cancha_ajena, usuario=superadmin).status_code == status.HTTP_201_CREATED

    def test_el_superadmin_hereda_el_permiso_aunque_no_lo_tenga_asignado(self, registrar, superadmin, cancha):
        RolPermiso.objects.get(rol__nombre='SUPERADMIN', permiso__codigo='gestionar_turnos_fijos').desactivar()

        assert registrar(cancha, usuario=superadmin).status_code == status.HTTP_201_CREATED

    def test_el_jugador_recibe_403(self, registrar, jugador, cancha):
        assert registrar(cancha, usuario=jugador).status_code == status.HTTP_403_FORBIDDEN

    def test_bloquea_la_cancha(self, registrar, cancha):
        from core.repositories import ReservaRepository

        with mock.patch.object(
            ReservaRepository, 'bloquear_cancha', wraps=ReservaRepository.bloquear_cancha,
        ) as bloquear:
            registrar(cancha)

        bloquear.assert_called_once_with(cancha.id)


class TestColisionesDeTurnosFijos:
    def test_choca_con_otro_turno_fijo_vigente(self, registrar, turno, cancha):
        respuesta = registrar(cancha, desde=_martes(3))

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == (
            'Se superpone con otro turno fijo vigente de la cancha (Martes de 21:00 a 22:00).'
        )
        assert TurnoFijo.objects.count() == 1

    def test_un_turno_fijo_pausado_o_de_baja_no_choca(self, registrar, crear_turno_fijo, cancha):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, estado=EstadoTurnoFijo.PAUSADO)
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, estado=EstadoTurnoFijo.BAJA)

        assert registrar(cancha).status_code == status.HTTP_201_CREATED

    def test_un_turno_con_fin_choca_con_uno_sin_fin(self, registrar, turno, cancha):
        assert registrar(cancha, hasta=_martes(2)).status_code == status.HTTP_409_CONFLICT

    def test_vigencias_sin_fechas_en_comun_no_chocan(self, registrar, crear_turno_fijo, cancha):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, hasta=_martes(2))

        assert registrar(cancha, desde=_martes(3)).status_code == status.HTTP_201_CREATED

    def test_vigencias_que_se_tocan_sin_un_martes_en_comun_no_chocan(self, registrar, crear_turno_fijo, cancha):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, hasta=_martes(1) + timedelta(days=3))

        assert registrar(cancha, desde=_martes(1) + timedelta(days=2)).status_code == status.HTTP_201_CREATED

    def test_horarios_contiguos_u_otra_cancha_no_chocan(
        self, registrar, crear_turno_fijo, complejo, crear_cancha, cancha,
    ):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(20, 0), time(21, 0), desde=MARTES)
        crear_turno_fijo(crear_cancha(complejo, 'Cancha 2'), DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES)

        assert registrar(cancha).status_code == status.HTTP_201_CREATED

    def test_choca_con_una_reserva_activa_futura_de_ese_dia_y_hora(self, registrar, crear_reserva, cancha):
        crear_reserva(cancha, _martes(2), time(21, 0), time(22, 0), estado=EstadoReserva.SENADA)

        respuesta = registrar(cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == 'Se superpone con una reserva activa del 01/12/2026 a las 21:00.'

    @pytest.mark.parametrize('estado', [EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.AUSENTE, EstadoReserva.BAJA])
    def test_una_reserva_no_ocupante_no_choca(self, registrar, crear_reserva, cancha, estado):
        crear_reserva(cancha, _martes(2), time(21, 0), time(22, 0), estado=estado)

        assert registrar(cancha).status_code == status.HTTP_201_CREATED

    def test_reservas_de_otro_dia_otro_horario_o_fuera_de_vigencia_no_chocan(self, registrar, crear_reserva, cancha):
        crear_reserva(cancha, _martes(1) + timedelta(days=1), time(21, 0), time(22, 0))
        crear_reserva(cancha, _martes(1), time(20, 0), time(21, 0))
        crear_reserva(cancha, _martes(6), time(21, 0), time(22, 0))

        assert registrar(cancha, hasta=_martes(5)).status_code == status.HTTP_201_CREATED

    def test_choca_con_una_excepcion_en_alguna_fecha_del_turno(
        self, registrar, crear_excepcion_horaria, complejo, cancha,
    ):
        crear_excepcion_horaria(complejo, _martes(3), tipo_motivo=TipoMotivoExcepcion.FERIADO)

        respuesta = registrar(cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == 'Coincide con una excepción horaria activa el 08/12/2026 (Feriado).'

    def test_una_excepcion_de_varios_dias_que_incluye_un_martes_choca(
        self, registrar, crear_excepcion_horaria, complejo, cancha,
    ):
        crear_excepcion_horaria(
            complejo, _martes(1) - timedelta(days=2), hasta=_martes(1) + timedelta(days=1),
            cancha=cancha, inicio=time(20, 0), fin=time(23, 0),
        )

        assert registrar(cancha).status_code == status.HTTP_409_CONFLICT

    def test_excepciones_que_no_caen_en_ese_dia_u_horario_no_chocan(
        self, registrar, crear_excepcion_horaria, complejo, crear_cancha, cancha,
    ):
        crear_excepcion_horaria(complejo, _martes(1) + timedelta(days=1), hasta=_martes(1) + timedelta(days=5))
        crear_excepcion_horaria(complejo, _martes(1), cancha=cancha, inicio=time(14, 0), fin=time(21, 0))
        crear_excepcion_horaria(complejo, _martes(1), cancha=crear_cancha(complejo, 'Cancha 2'))
        crear_excepcion_horaria(complejo, _martes(1)).desactivar()
        crear_excepcion_horaria(complejo, _martes(9))

        assert registrar(cancha, hasta=_martes(8)).status_code == status.HTTP_201_CREATED

    def test_un_turno_fijo_ocupa_la_grilla_y_bloquea_reservas_web(
        self, registrar, jugador, cliente, cliente_de, complejo, cancha,
    ):
        registrar(cancha)

        grilla = cliente.get(f'/api/complejos/{complejo.id}/grilla/?fecha={_martes(2).isoformat()}').json()
        bloques = {bloque['hora_inicio']: bloque['estado'] for bloque in grilla['canchas'][0]['bloques']}
        reserva = cliente_de(jugador).post(URL_RESERVAS, {
            'cancha': cancha.id, 'fecha_turno': _martes(2).isoformat(), 'hora_inicio': '21:00',
        }, format='json')

        assert bloques['21:00:00'] == 'OCUPADO'
        assert reserva.status_code == status.HTTP_409_CONFLICT


class TestEdicionDeTurnosFijos:
    def _patch(self, cliente_de, usuario, turno, **datos):
        return cliente_de(usuario).patch(_url(turno), datos, format='json')

    def test_edita_el_contacto_del_cliente(self, reloj, operador, cliente_de, turno):
        respuesta = self._patch(
            cliente_de, operador, turno, nombre_cliente_manual='Los <b>del</b> Martes 2', telefono_cliente_manual='3777 000402',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        turno.refresh_from_db()
        assert (turno.nombre_cliente_manual, turno.telefono_cliente_manual) == ('Los del Martes 2', '3777 000402')

    def test_cambiar_el_dia_el_horario_o_la_cancha_responde_400(
        self, reloj, dueno, cliente_de, crear_cancha, complejo, turno,
    ):
        respuesta = self._patch(
            cliente_de, dueno, turno, dia_semana=DiaSemana.JUEVES, hora_inicio='14:00',
            fecha_inicio_vigencia='2026-12-01', cancha=crear_cancha(complejo, 'Cancha 2').id,
            nombre_cliente_manual='Otro nombre',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert set(respuesta.json()['detail']) == {'dia_semana', 'hora_inicio', 'fecha_inicio_vigencia', 'cancha'}
        assert respuesta.json()['detail']['hora_inicio'] == ['No se edita: dá de baja el turno fijo y registrá otro.']
        turno.refresh_from_db()
        assert (turno.dia_semana, turno.hora_inicio, turno.nombre_cliente_manual) == (
            DiaSemana.MARTES, time(21, 0), 'Los del Martes',
        )

    def test_reenviar_los_mismos_valores_no_es_un_error(self, reloj, dueno, cliente_de, cancha, turno):
        respuesta = self._patch(
            cliente_de, dueno, turno, cancha=cancha.id, dia_semana=DiaSemana.MARTES, hora_inicio='21:00',
            fecha_inicio_vigencia=MARTES.isoformat(), estado=EstadoTurnoFijo.PAUSADO,
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoTurnoFijo.PAUSADO

    def test_sin_cambios_reales_no_modifica_ni_anuncia(
        self, reloj, dueno, cliente_de, turno, django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks() as pendientes:
            respuesta = self._patch(cliente_de, dueno, turno, nombre_cliente_manual='Los del Martes', hora_inicio='21:00')

        assert respuesta.status_code == status.HTTP_200_OK
        assert pendientes == []

    def test_trae_los_de_una_fecha_con_o_sin_los_pausados(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha, turno):
        pausado = crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(15, 0), time(16, 0), desde=MARTES, estado=EstadoTurnoFijo.PAUSADO,
        )
        api = cliente_de(dueno)

        todos = _ids(api.get(URL, {'fecha': _martes(1).isoformat()}))
        vigentes = _ids(api.get(URL, {'fecha': _martes(1).isoformat(), 'estado': EstadoTurnoFijo.VIGENTE}))

        assert set(todos) == {turno.id, pausado.id}
        assert vigentes == [turno.id]

    def test_pausar_libera_el_horario(self, reloj, dueno, jugador, cliente_de, turno, cancha):
        respuesta = self._patch(cliente_de, dueno, turno, estado=EstadoTurnoFijo.PAUSADO)
        reserva = cliente_de(jugador).post(URL_RESERVAS, {
            'cancha': cancha.id, 'fecha_turno': _martes(1).isoformat(), 'hora_inicio': '21:00',
        }, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado_nombre'] == 'Pausado'
        assert reserva.status_code == status.HTTP_201_CREATED

    def test_reanudar_revisa_toda_la_vigencia(self, reloj, dueno, crear_reserva, cliente_de, turno, cancha):
        turno.estado = EstadoTurnoFijo.PAUSADO
        turno.save()
        crear_reserva(cancha, _martes(5), time(21, 0), time(22, 0))

        respuesta = self._patch(cliente_de, dueno, turno, estado=EstadoTurnoFijo.VIGENTE)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        turno.refresh_from_db()
        assert turno.estado == EstadoTurnoFijo.PAUSADO

    def test_reanudar_sin_conflictos_vuelve_a_ocupar(self, reloj, dueno, cliente_de, turno):
        turno.estado = EstadoTurnoFijo.PAUSADO
        turno.save()

        assert self._patch(cliente_de, dueno, turno, estado=EstadoTurnoFijo.VIGENTE).status_code == 200

    def test_reanudar_un_turno_ya_vencido_no_revisa_fechas_pasadas(
        self, reloj, dueno, crear_turno_fijo, crear_reserva, cliente_de, cancha,
    ):
        turno = crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=date(2026, 11, 3), hasta=date(2026, 11, 10),
            estado=EstadoTurnoFijo.PAUSADO,
        )
        crear_reserva(cancha, date(2026, 11, 10), time(21, 0), time(22, 0), estado=EstadoReserva.COMPLETADA)

        assert self._patch(cliente_de, dueno, turno, estado=EstadoTurnoFijo.VIGENTE).status_code == 200

    def test_un_turno_dado_de_baja_al_bloquear_responde_404(self, reloj, turno):
        turno.desactivar()

        with pytest.raises(NotFound):
            TurnoFijoService.actualizar(turno, {'estado': EstadoTurnoFijo.PAUSADO})

    def test_extender_el_fin_revisa_solo_el_tramo_agregado(
        self, reloj, dueno, crear_reserva, crear_turno_fijo, crear_excepcion_horaria, cliente_de, complejo, cancha,
    ):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, hasta=_martes(2))
        # Un cierre posterior al alta, dentro de la vigencia original, no impide extenderla.
        crear_excepcion_horaria(complejo, _martes(1))
        crear_reserva(cancha, _martes(4), time(21, 0), time(22, 0))

        sin_conflicto = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=_martes(3).isoformat())
        con_conflicto = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=_martes(4).isoformat())
        sin_fin = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=None)

        assert sin_conflicto.status_code == status.HTTP_200_OK
        assert con_conflicto.status_code == status.HTTP_409_CONFLICT
        assert sin_fin.status_code == status.HTTP_409_CONFLICT
        turno.refresh_from_db()
        assert turno.fecha_fin_vigencia == _martes(3)

    def test_acortar_el_fin_no_revisa_conflictos(self, reloj, dueno, crear_excepcion_horaria, cliente_de, complejo, turno):
        crear_excepcion_horaria(complejo, _martes(1))

        respuesta = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=_martes(3).isoformat())

        assert respuesta.status_code == status.HTTP_200_OK

    def test_el_fin_no_puede_quedar_en_el_pasado(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        turno = crear_turno_fijo(cancha, DiaSemana.LUNES, time(14, 0), time(15, 0), desde=HOY - timedelta(days=14))

        respuesta = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=(HOY - timedelta(days=7)).isoformat())

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_el_fin_no_puede_ser_anterior_al_inicio(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=_martes(1))

        respuesta = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=HOY.isoformat())

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_el_fin_debe_dejar_algun_martes(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES + timedelta(days=1))

        respuesta = self._patch(cliente_de, dueno, turno, fecha_fin_vigencia=(MARTES + timedelta(days=3)).isoformat())

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail']['fecha_fin_vigencia'] == 'La vigencia no incluye ningún martes.'

    def test_la_baja_logica_no_se_hace_por_patch(self, reloj, dueno, cliente_de, turno):
        assert self._patch(cliente_de, dueno, turno, estado=EstadoTurnoFijo.BAJA).status_code == 400

    def test_un_turno_ajeno_responde_404(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha_ajena):
        ajeno = crear_turno_fijo(cancha_ajena, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=MARTES)

        assert self._patch(cliente_de, dueno, ajeno, estado=EstadoTurnoFijo.PAUSADO).status_code == 404

    def test_sin_gestionar_turnos_fijos_recibe_403(self, reloj, operador, cliente_de, turno):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='gestionar_turnos_fijos').desactivar()

        assert self._patch(cliente_de, operador, turno, estado=EstadoTurnoFijo.PAUSADO).status_code == 403

    def test_pausar_se_anuncia_con_la_vigencia(
        self, reloj, dueno, cliente_de, complejo, cancha, turno, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                self._patch(cliente_de, dueno, turno, estado=EstadoTurnoFijo.PAUSADO)
                self._patch(cliente_de, dueno, turno, nombre_cliente_manual='Otro nombre')

        publicar.assert_called_once_with(complejo.id, {
            'event': 'grilla_actualizada',
            'cancha_id': cancha.id,
            'fecha_desde': MARTES.isoformat(),
            'fecha_hasta': None,
            'hora_inicio': '21:00:00',
            'hora_fin': '22:00:00',
        })


class TestBajaDeTurnosFijos:
    def test_la_baja_es_logica(self, reloj, dueno, cliente_de, turno):
        respuesta = cliente_de(dueno).delete(_url(turno))

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        turno.refresh_from_db()
        assert turno.estado == EstadoTurnoFijo.BAJA

    def test_libera_el_horario_y_conserva_las_fechas_ya_registradas(
        self, reloj, dueno, jugador, crear_reserva, cliente_de, turno, cancha,
    ):
        generada = crear_reserva(
            cancha, _martes(0), time(21, 0), time(22, 0), usuario=None, turno_fijo=turno,
            tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
        )

        cliente_de(dueno).delete(_url(turno))
        reserva = cliente_de(jugador).post(URL_RESERVAS, {
            'cancha': cancha.id, 'fecha_turno': _martes(1).isoformat(), 'hora_inicio': '21:00',
        }, format='json')

        assert reserva.status_code == status.HTTP_201_CREATED
        generada.refresh_from_db()
        assert generada.estado == EstadoReserva.CONFIRMADA

    def test_un_turno_ajeno_o_ya_dado_de_baja_responde_404(
        self, reloj, dueno, crear_turno_fijo, cliente_de, cancha_ajena, turno,
    ):
        ajeno = crear_turno_fijo(cancha_ajena, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=MARTES)
        api = cliente_de(dueno)
        api.delete(_url(turno))

        assert api.delete(_url(ajeno)).status_code == status.HTTP_404_NOT_FOUND
        assert api.delete(_url(turno)).status_code == status.HTTP_404_NOT_FOUND

    def test_el_jugador_recibe_403(self, reloj, jugador, cliente_de, turno):
        assert cliente_de(jugador).delete(_url(turno)).status_code == status.HTTP_403_FORBIDDEN

    def test_la_baja_se_anuncia(self, reloj, dueno, cliente_de, turno, django_capture_on_commit_callbacks):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                cliente_de(dueno).delete(_url(turno))

        publicar.assert_called_once()


class TestFechasDeTurnoFijo:
    def _registrar_fecha(self, cliente_de, usuario, turno, fecha):
        return cliente_de(usuario).post(_url(turno, 'fechas/'), {'fecha_turno': fecha.isoformat()}, format='json')

    def test_lleva_una_fecha_a_la_agenda(self, reloj, operador, cliente_de, turno):
        respuesta = self._registrar_fecha(cliente_de, operador, turno, _martes(1))

        assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['turno_fijo'] == turno.id
        assert cuerpo['tipo_ocupacion'] == TipoOcupacion.TURNO_FIJO
        assert cuerpo['estado'] == EstadoReserva.CONFIRMADA
        assert (cuerpo['hora_inicio'], cuerpo['hora_fin']) == ('21:00:00', '22:00:00')
        assert cuerpo['precio_acordado'] == '45000.00'
        assert cuerpo['cliente'] == {'nombre': 'Los del Martes', 'telefono': '3777 000401', 'email': None}
        assert Reserva.objects.get().creado_por == operador

    def test_cancelar_la_fecha_libera_solo_ese_casillero(self, reloj, operador, jugador, cliente, cliente_de, complejo, turno, cancha):
        reserva_id = self._registrar_fecha(cliente_de, operador, turno, _martes(1)).json()['id']
        cliente_de(operador).post(f'/api/agenda/{reserva_id}/cancelar/')

        def _estado(fecha):
            grilla = cliente.get(f'/api/complejos/{complejo.id}/grilla/?fecha={fecha.isoformat()}').json()
            return {b['hora_inicio']: b['estado'] for b in grilla['canchas'][0]['bloques']}['21:00:00']

        reserva = cliente_de(jugador).post(URL_RESERVAS, {
            'cancha': cancha.id, 'fecha_turno': _martes(1).isoformat(), 'hora_inicio': '21:00',
        }, format='json')

        assert reserva.status_code == status.HTTP_201_CREATED
        assert _estado(_martes(2)) == 'OCUPADO'

    def test_una_fecha_ya_registrada_responde_409(self, reloj, dueno, cliente_de, turno):
        self._registrar_fecha(cliente_de, dueno, turno, _martes(1))

        assert self._registrar_fecha(cliente_de, dueno, turno, _martes(1)).status_code == status.HTTP_409_CONFLICT

    def test_una_fecha_cancelada_tampoco_se_vuelve_a_registrar(self, reloj, dueno, cliente_de, turno):
        reserva_id = self._registrar_fecha(cliente_de, dueno, turno, _martes(1)).json()['id']
        cliente_de(dueno).post(f'/api/agenda/{reserva_id}/cancelar/')

        assert self._registrar_fecha(cliente_de, dueno, turno, _martes(1)).status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize('fecha', [
        MARTES + timedelta(days=1), HOY, date(2026, 11, 10),
    ], ids=['otro-dia', 'antes-de-la-vigencia', 'martes-anterior'])
    def test_la_fecha_debe_ser_un_dia_del_turno_dentro_de_su_vigencia(self, reloj, dueno, cliente_de, turno, fecha):
        respuesta = self._registrar_fecha(cliente_de, dueno, turno, fecha)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_turno' in respuesta.json()['detail']

    def test_una_fecha_despues_del_fin_responde_400(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, hasta=_martes(2))

        assert self._registrar_fecha(cliente_de, dueno, turno, _martes(3)).status_code == 400

    def test_registra_una_fecha_pasada_para_cerrarla(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=date(2026, 11, 3))

        respuesta = self._registrar_fecha(cliente_de, dueno, turno, date(2026, 11, 10))
        cierre = cliente_de(dueno).patch(
            f'/api/agenda/{respuesta.json()["id"]}/', {'estado': EstadoReserva.COMPLETADA}, format='json',
        )

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert cierre.status_code == status.HTTP_200_OK

    def test_un_turno_pausado_no_registra_fechas(self, reloj, dueno, cliente_de, turno):
        turno.estado = EstadoTurnoFijo.PAUSADO
        turno.save()

        assert self._registrar_fecha(cliente_de, dueno, turno, _martes(1)).status_code == 400

    def test_un_rango_sin_precio_diferenciado_cobra_el_precio_base(
        self, reloj, dueno, crear_turno_fijo, cliente_de, cancha,
    ):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(15, 0), time(16, 0), desde=MARTES)

        respuesta = self._registrar_fecha(cliente_de, dueno, turno, _martes(1))

        assert respuesta.json()['precio_acordado'] == '38000.00'

    def test_sin_rango_que_contenga_el_turno_cobra_el_precio_base(self, reloj, dueno, cliente_de, turno, cancha):
        cancha.horarios.filter(hora_apertura=time(18, 0)).get().desactivar()

        respuesta = self._registrar_fecha(cliente_de, dueno, turno, _martes(1))

        assert respuesta.json()['precio_acordado'] == '38000.00'

    def test_un_turno_ajeno_responde_404(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha_ajena):
        ajeno = crear_turno_fijo(cancha_ajena, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=MARTES)

        assert self._registrar_fecha(cliente_de, dueno, ajeno, _martes(1)).status_code == 404

    def test_el_jugador_recibe_403(self, reloj, jugador, cliente_de, turno):
        assert self._registrar_fecha(cliente_de, jugador, turno, _martes(1)).status_code == 403

    def test_se_audita_sin_datos_del_cliente(self, reloj, dueno, cliente_de, complejo, turno):
        self._registrar_fecha(cliente_de, dueno, turno, _martes(1))

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CREADA)
        assert log.complejo == complejo
        assert f'Turno fijo id {turno.id}.' in log.detalle
        assert 'Los del Martes' not in log.detalle and '000401' not in log.detalle
