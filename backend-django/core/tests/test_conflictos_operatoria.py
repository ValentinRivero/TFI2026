import json
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import (
    DiaSemana,
    DuracionTurno,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    EstadoTurnoFijo,
    LogAuditoria,
    TipoEventoAuditoria,
)
from core.repositories import CanchaRepository
from core.services import MOTIVO_CANCHA_EN_MANTENIMIENTO, MOTIVO_FUERA_DE_LOS_TURNOS, DifusionGrillaService

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)
URL_AGENDA = '/api/agenda/'


@pytest.fixture(autouse=True)
def lunes_a_las_diez(reloj):
    """Todo el archivo razona sobre el lunes congelado de conftest."""
    return reloj


@pytest.fixture
def cancha(complejo, crear_cancha):
    return crear_cancha(complejo, 'Cancha 1')


@pytest.fixture
def horario(cancha, crear_horario):
    """Martes de 14 a 23, turnos de 60 minutos."""
    return crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))


@pytest.fixture
def reserva_tarde(reloj, crear_reserva, cancha, horario):
    return crear_reserva(cancha, MARTES, time(20, 0), time(21, 0), estado=EstadoReserva.SENADA)


@pytest.fixture
def reserva_temprano(reloj, crear_reserva, cancha, horario):
    return crear_reserva(cancha, MARTES, time(15, 0), time(16, 0), estado=EstadoReserva.CONFIRMADA)


def _patch_horario(api, horario, **datos):
    return api.patch(f'/api/horarios/{horario.id}/', datos, format='json')


def _ids_reservas(respuesta):
    return [reserva['id'] for reserva in respuesta.json()['conflictos']['reservas']]


def _agenda(api):
    return {reserva['id']: reserva for reserva in api.get(URL_AGENDA).json()['results']}


class TestCambioDeHorario:
    def test_acortar_un_rango_con_reservas_afectadas_responde_409_con_el_detalle(
        self, dueno, cliente_de, horario, reserva_tarde, reserva_temprano,
    ):
        respuesta = _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00')

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        cuerpo = respuesta.json()
        assert cuerpo['error'] is True and cuerpo['requiere_confirmacion'] is True
        assert '"confirmar": true' in cuerpo['detail']
        assert cuerpo['conflictos'] == {
            'cantidad': 1,
            'reservas': [{
                'id': reserva_tarde.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '20:00:00',
                'estado': EstadoReserva.SENADA, 'motivo': MOTIVO_FUERA_DE_LOS_TURNOS,
            }],
            'turnos_fijos': [],
        }
        horario.refresh_from_db()
        assert horario.hora_cierre == time(23, 0)

    def test_el_409_no_lleva_datos_personales(self, dueno, cliente_de, horario, reserva_tarde):
        texto = json.dumps(_patch_horario(cliente_de(dueno), horario, hora_cierre='19:00').json())

        for dato in ('jugador@talibre.test', 'Jugador Prueba', 'precio', 'observaciones'):
            assert dato not in texto

    def test_con_confirmar_aplica_el_cambio_y_conserva_las_reservas(
        self, dueno, cliente_de, horario, reserva_tarde, reserva_temprano,
    ):
        respuesta = _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00', confirmar=True)

        assert respuesta.status_code == status.HTTP_200_OK
        horario.refresh_from_db()
        reserva_tarde.refresh_from_db()
        assert horario.hora_cierre == time(19, 0)
        assert reserva_tarde.estado == EstadoReserva.SENADA

    def test_las_reservas_afectadas_quedan_marcadas_en_la_agenda(
        self, dueno, cliente_de, horario, reserva_tarde, reserva_temprano,
    ):
        api = cliente_de(dueno)
        _patch_horario(api, horario, hora_cierre='19:00', confirmar=True)

        agenda = _agenda(api)

        assert agenda[reserva_tarde.id]['conflicto_operatoria'] == MOTIVO_FUERA_DE_LOS_TURNOS
        assert agenda[reserva_temprano.id]['conflicto_operatoria'] is None

    def test_un_cambio_que_no_afecta_reservas_se_aplica_sin_confirmar(self, dueno, cliente_de, horario, reserva_tarde):
        assert _patch_horario(cliente_de(dueno), horario, hora_cierre='21:00').status_code == status.HTTP_200_OK

    def test_correr_la_apertura_desalinea_los_turnos(self, dueno, cliente_de, horario, reserva_tarde, reserva_temprano):
        respuesta = _patch_horario(cliente_de(dueno), horario, hora_apertura='14:30')

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert set(_ids_reservas(respuesta)) == {reserva_tarde.id, reserva_temprano.id}

    def test_mover_el_rango_a_otro_dia_afecta_las_reservas_de_ese_dia(self, dueno, cliente_de, horario, reserva_tarde):
        respuesta = _patch_horario(cliente_de(dueno), horario, dia_semana=DiaSemana.MIERCOLES)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert _ids_reservas(respuesta) == [reserva_tarde.id]

    def test_cambiar_solo_el_precio_no_revisa_conflictos(self, dueno, cliente_de, horario, reserva_tarde):
        respuesta = _patch_horario(cliente_de(dueno), horario, precio_diferenciado='45000.00')

        assert respuesta.status_code == status.HTTP_200_OK

    def test_ignora_reservas_pasadas_canceladas_completadas_o_ya_iniciadas(
        self, reloj, dueno, crear_reserva, crear_horario, cliente_de, cancha, horario,
    ):
        crear_reserva(cancha, MARTES, time(20, 0), time(21, 0), estado=EstadoReserva.CANCELADA_JUGADOR)
        crear_reserva(cancha, MARTES - timedelta(days=7), time(20, 0), time(21, 0))
        crear_reserva(cancha, MARTES, time(21, 0), time(22, 0), estado=EstadoReserva.COMPLETADA)
        lunes = crear_horario(cancha, DiaSemana.LUNES, time(9, 0), time(12, 0))
        crear_reserva(cancha, HOY, time(9, 0), time(10, 0))

        api = cliente_de(dueno)

        assert _patch_horario(api, horario, hora_cierre='19:00').status_code == status.HTTP_200_OK
        assert _patch_horario(api, lunes, hora_cierre='10:00').status_code == status.HTTP_200_OK

    def test_informa_los_turnos_fijos_afectados(self, dueno, crear_turno_fijo, cliente_de, cancha, horario):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES)
        pausado = crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(22, 0), time(23, 0), desde=MARTES, estado=EstadoTurnoFijo.PAUSADO,
        )
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(20, 0), time(21, 0), desde=HOY - timedelta(days=14),
                         hasta=HOY - timedelta(days=1))

        respuesta = _patch_horario(cliente_de(dueno), horario, hora_cierre='20:00')

        conflictos = respuesta.json()['conflictos']
        assert conflictos['cantidad'] == 2 and conflictos['reservas'] == []
        assert conflictos['turnos_fijos'] == [
            {'id': turno.id, 'dia_semana': DiaSemana.MARTES, 'hora_inicio': '21:00:00',
             'motivo': MOTIVO_FUERA_DE_LOS_TURNOS},
            {'id': pausado.id, 'dia_semana': DiaSemana.MARTES, 'hora_inicio': '22:00:00',
             'motivo': MOTIVO_FUERA_DE_LOS_TURNOS},
        ]

    def test_lo_ya_marcado_no_vuelve_a_frenar_otro_cambio(self, dueno, cliente_de, horario, reserva_tarde):
        api = cliente_de(dueno)
        _patch_horario(api, horario, hora_cierre='19:00', confirmar=True)

        assert _patch_horario(api, horario, hora_cierre='18:00').status_code == status.HTTP_200_OK

    def test_un_motivo_nuevo_sobre_lo_ya_marcado_vuelve_a_pedir_confirmacion(
        self, dueno, cliente_de, cancha, horario, reserva_tarde,
    ):
        api = cliente_de(dueno)
        _patch_horario(api, horario, hora_cierre='19:00', confirmar=True)

        respuesta = api.patch(f'/api/canchas/{cancha.id}/', {'estado': EstadoCancha.EN_MANTENIMIENTO}, format='json')

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        (reserva,) = respuesta.json()['conflictos']['reservas']
        assert (reserva['id'], reserva['motivo']) == (reserva_tarde.id, MOTIVO_CANCHA_EN_MANTENIMIENTO)

    def test_volver_al_horario_original_quita_la_marca(self, dueno, cliente_de, horario, reserva_tarde):
        api = cliente_de(dueno)
        _patch_horario(api, horario, hora_cierre='19:00', confirmar=True)
        _patch_horario(api, horario, hora_cierre='23:00')

        assert _agenda(api)[reserva_tarde.id]['conflicto_operatoria'] is None

    def test_el_cambio_confirmado_se_audita_sin_datos_personales(
        self, dueno, cliente_de, complejo, cancha, horario, reserva_tarde,
    ):
        _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00', confirmar=True)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION)
        assert log.usuario == dueno and log.complejo == complejo
        assert f'Cancha id {cancha.id}: edición del horario id {horario.id}.' in log.detalle
        assert f'Reservas afectadas: [{reserva_tarde.id}]' in log.detalle
        assert 'jugador@talibre.test' not in log.detalle

    def test_sin_conflictos_no_se_audita(self, dueno, cliente_de, horario):
        _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00', confirmar=True)

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION).exists()

    @pytest.mark.parametrize('valor', ['quizas', 3])
    def test_un_confirmar_invalido_responde_400(self, dueno, cliente_de, horario, reserva_tarde, valor):
        respuesta = _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00', confirmar=valor)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'confirmar' in respuesta.json()['detail']

    def test_bloquea_la_cancha_antes_de_calcular(self, dueno, cliente_de, cancha, horario, reserva_tarde):
        with mock.patch.object(CanchaRepository, 'bloquear', wraps=CanchaRepository.bloquear) as bloquear:
            _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00')

        bloquear.assert_called_once_with(cancha.id)


class TestBajaDeHorario:
    def test_dar_de_baja_un_rango_con_reservas_responde_409(self, dueno, cliente_de, horario, reserva_tarde):
        respuesta = cliente_de(dueno).delete(f'/api/horarios/{horario.id}/')

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert _ids_reservas(respuesta) == [reserva_tarde.id]
        horario.refresh_from_db()
        assert horario.estado == EstadoRegistro.ACTIVO

    @pytest.mark.parametrize('forma', ['query', 'cuerpo'])
    def test_con_confirmar_se_da_de_baja_y_conserva_las_reservas(
        self, dueno, cliente_de, horario, reserva_tarde, forma,
    ):
        api = cliente_de(dueno)
        if forma == 'query':
            respuesta = api.delete(f'/api/horarios/{horario.id}/?confirmar=true')
        else:
            respuesta = api.delete(f'/api/horarios/{horario.id}/', {'confirmar': True}, format='json')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        horario.refresh_from_db()
        reserva_tarde.refresh_from_db()
        assert horario.estado == EstadoRegistro.BAJA
        assert reserva_tarde.estado == EstadoReserva.SENADA
        assert _agenda(api)[reserva_tarde.id]['conflicto_operatoria'] == MOTIVO_FUERA_DE_LOS_TURNOS

    def test_un_rango_sin_reservas_se_da_de_baja_sin_confirmar(
        self, dueno, cliente_de, crear_horario, cancha, horario, reserva_tarde,
    ):
        otro = crear_horario(cancha, DiaSemana.JUEVES, time(14, 0), time(23, 0))

        assert cliente_de(dueno).delete(f'/api/horarios/{otro.id}/').status_code == status.HTTP_204_NO_CONTENT


class TestCambioDeCancha:
    def _patch(self, api, cancha, **datos):
        return api.patch(f'/api/canchas/{cancha.id}/', datos, format='json')

    def test_cambiar_la_duracion_desalinea_las_reservas(
        self, dueno, cliente_de, cancha, horario, reserva_tarde, reserva_temprano,
    ):
        respuesta = self._patch(cliente_de(dueno), cancha, duracion_turno_min=DuracionTurno.NOVENTA)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert set(_ids_reservas(respuesta)) == {reserva_tarde.id, reserva_temprano.id}
        cancha.refresh_from_db()
        assert cancha.duracion_turno_min == DuracionTurno.SESENTA

    def test_con_confirmar_cambia_la_duracion_y_marca_las_reservas(
        self, dueno, cliente_de, cancha, horario, reserva_tarde,
    ):
        api = cliente_de(dueno)

        respuesta = self._patch(api, cancha, duracion_turno_min=DuracionTurno.NOVENTA, confirmar=True)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['duracion_turno_min'] == DuracionTurno.NOVENTA
        assert _agenda(api)[reserva_tarde.id]['conflicto_operatoria'] == MOTIVO_FUERA_DE_LOS_TURNOS

    def test_pasar_a_mantenimiento_afecta_todas_las_reservas_futuras(
        self, dueno, crear_turno_fijo, cliente_de, cancha, horario, reserva_tarde, reserva_temprano,
    ):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(22, 0), time(23, 0), desde=MARTES)

        respuesta = self._patch(cliente_de(dueno), cancha, estado=EstadoCancha.EN_MANTENIMIENTO)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        conflictos = respuesta.json()['conflictos']
        assert conflictos['cantidad'] == 3
        assert [item['id'] for item in conflictos['turnos_fijos']] == [turno.id]

    def test_con_confirmar_queda_en_mantenimiento_y_todo_marcado(
        self, dueno, crear_turno_fijo, cliente_de, cancha, horario, reserva_tarde,
    ):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(22, 0), time(23, 0), desde=MARTES)
        api = cliente_de(dueno)

        respuesta = self._patch(api, cancha, estado=EstadoCancha.EN_MANTENIMIENTO, confirmar=True)
        turnos = {item['id']: item for item in api.get('/api/turnos-fijos/').json()['results']}

        assert respuesta.status_code == status.HTTP_200_OK
        assert _agenda(api)[reserva_tarde.id]['conflicto_operatoria'] == MOTIVO_CANCHA_EN_MANTENIMIENTO
        assert turnos[turno.id]['conflicto_operatoria'] == MOTIVO_CANCHA_EN_MANTENIMIENTO

    def test_reactivar_la_cancha_no_pide_confirmacion_y_quita_la_marca(
        self, dueno, cliente_de, cancha, horario, reserva_tarde,
    ):
        api = cliente_de(dueno)
        self._patch(api, cancha, estado=EstadoCancha.EN_MANTENIMIENTO, confirmar=True)

        respuesta = self._patch(api, cancha, estado=EstadoCancha.ACTIVA)

        assert respuesta.status_code == status.HTTP_200_OK
        assert _agenda(api)[reserva_tarde.id]['conflicto_operatoria'] is None

    def test_cambios_que_no_tocan_la_operatoria_no_revisan_conflictos(
        self, dueno, cliente_de, cancha, horario, reserva_tarde,
    ):
        respuesta = self._patch(cliente_de(dueno), cancha, nombre='Cancha Central', precio_base='40000.00')

        assert respuesta.status_code == status.HTTP_200_OK

    def test_la_baja_de_una_cancha_con_reservas_sigue_siendo_400_aun_confirmando(
        self, dueno, cliente_de, cancha, horario, reserva_tarde,
    ):
        respuesta = cliente_de(dueno).delete(f'/api/canchas/{cancha.id}/?confirmar=true')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        cancha.refresh_from_db()
        assert cancha.estado == EstadoCancha.ACTIVA

    def test_el_operador_no_cambia_la_duracion(self, operador, cliente_de, cancha, horario, reserva_tarde):
        respuesta = self._patch(cliente_de(operador), cancha, duracion_turno_min=DuracionTurno.NOVENTA, confirmar=True)

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN


class TestMarcasEnLaAgenda:
    def test_filtra_las_reservas_con_conflicto(self, dueno, cliente_de, horario, reserva_tarde, reserva_temprano):
        api = cliente_de(dueno)
        _patch_horario(api, horario, hora_cierre='19:00', confirmar=True)

        con = [r['id'] for r in api.get(URL_AGENDA, {'con_conflicto': 'true'}).json()['results']]
        sin = [r['id'] for r in api.get(URL_AGENDA, {'con_conflicto': 'false'}).json()['results']]

        assert con == [reserva_tarde.id]
        assert sin == [reserva_temprano.id]

    def test_una_reserva_resuelta_deja_de_estar_marcada(self, dueno, cliente_de, horario, reserva_tarde):
        api = cliente_de(dueno)
        _patch_horario(api, horario, hora_cierre='19:00', confirmar=True)

        cancelada = api.post(f'{URL_AGENDA}{reserva_tarde.id}/cancelar/').json()

        assert cancelada['conflicto_operatoria'] is None
        assert api.get(URL_AGENDA, {'con_conflicto': 'true'}).json()['count'] == 0

    def test_un_turno_fijo_vencido_no_se_marca(self, dueno, crear_turno_fijo, cliente_de, cancha, horario):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=HOY - timedelta(days=13),
                         hasta=HOY - timedelta(days=6))
        cancha.estado = EstadoCancha.EN_MANTENIMIENTO
        cancha.save()

        (turno,) = cliente_de(dueno).get('/api/turnos-fijos/').json()['results']

        assert turno['conflicto_operatoria'] is None


class TestDifusionDeLaOperatoria:
    def _eventos(self, captura, operacion):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with captura(execute=True):
                operacion()
        return [llamada.args for llamada in publicar.call_args_list]

    def _esperado(self, cancha_id):
        return {
            'event': 'grilla_actualizada', 'cancha_id': cancha_id, 'fecha_desde': HOY.isoformat(),
            'fecha_hasta': None, 'hora_inicio': None, 'hora_fin': None,
        }

    def test_los_cambios_de_horarios_se_anuncian(
        self, reloj, dueno, cliente_de, complejo, cancha, horario, django_capture_on_commit_callbacks,
    ):
        api = cliente_de(dueno)
        datos = {'cancha': cancha.id, 'dia_semana': DiaSemana.JUEVES, 'hora_apertura': '10:00', 'hora_cierre': '12:00'}

        alta = self._eventos(django_capture_on_commit_callbacks, lambda: api.post('/api/horarios/', datos, format='json'))
        edicion = self._eventos(django_capture_on_commit_callbacks, lambda: _patch_horario(api, horario, hora_cierre='22:00'))
        baja = self._eventos(django_capture_on_commit_callbacks, lambda: api.delete(f'/api/horarios/{horario.id}/'))

        for eventos in (alta, edicion, baja):
            assert eventos == [(complejo.id, self._esperado(cancha.id))]

    def test_los_cambios_de_canchas_se_anuncian(
        self, reloj, dueno, cliente_de, complejo, cancha, django_capture_on_commit_callbacks,
    ):
        api = cliente_de(dueno)

        edicion = self._eventos(
            django_capture_on_commit_callbacks,
            lambda: api.patch(f'/api/canchas/{cancha.id}/', {'precio_base': '41000.00'}, format='json'),
        )
        baja = self._eventos(django_capture_on_commit_callbacks, lambda: api.delete(f'/api/canchas/{cancha.id}/'))

        assert edicion == [(complejo.id, self._esperado(cancha.id))]
        assert baja == [(complejo.id, self._esperado(cancha.id))]

    def test_el_alta_de_una_cancha_se_anuncia(self, reloj, dueno, cliente_de, complejo, django_capture_on_commit_callbacks):
        from core.models import Deporte

        datos = {
            'complejo': complejo.id, 'deporte': Deporte.objects.get(nombre='Pádel').id, 'nombre': 'Pádel 1',
            'tipo_superficie': 1, 'cobertura': 1, 'iluminacion': 3, 'duracion_turno_min': 90, 'precio_base': '30000.00',
        }

        eventos = self._eventos(
            django_capture_on_commit_callbacks, lambda: cliente_de(dueno).post('/api/canchas/', datos, format='json'),
        )

        ((complejo_id, evento),) = eventos
        assert complejo_id == complejo.id and evento['fecha_hasta'] is None

    def test_un_cambio_rechazado_no_anuncia_nada(
        self, dueno, cliente_de, horario, reserva_tarde, django_capture_on_commit_callbacks,
    ):
        eventos = self._eventos(
            django_capture_on_commit_callbacks, lambda: _patch_horario(cliente_de(dueno), horario, hora_cierre='19:00'),
        )

        assert eventos == []

    def test_reactivar_un_contrato_anuncia_todo_el_complejo(
        self, reloj, superadmin, cliente_de, complejo, django_capture_on_commit_callbacks,
    ):
        complejo.estado_contrato = EstadoContrato.SUSPENDIDO
        complejo.save()

        eventos = self._eventos(
            django_capture_on_commit_callbacks,
            lambda: cliente_de(superadmin).patch(
                f'/api/contratos/{complejo.id}/', {'estado_contrato': EstadoContrato.ACTIVO}, format='json',
            ),
        )

        assert eventos == [(complejo.id, self._esperado(None))]


def test_el_precio_diferenciado_no_altera_las_reservas_ya_tomadas(dueno, cliente_de, horario, reserva_tarde):
    _patch_horario(cliente_de(dueno), horario, precio_diferenciado='99000.00')

    reserva_tarde.refresh_from_db()
    assert reserva_tarde.precio_acordado == Decimal('38000.00')


class TestCostoDeLaValidacion:
    def test_lee_reservas_turnos_y_horarios_una_sola_vez(
        self, dueno, crear_turno_fijo, cancha, horario, reserva_tarde, reserva_temprano,
    ):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from core.services import ConflictoOperatoriaService

        crear_turno_fijo(cancha, DiaSemana.MARTES, time(22, 0), time(23, 0), desde=MARTES)

        with CaptureQueriesContext(connection) as capturadas:
            ConflictoOperatoriaService.validar_cambio(cancha, True, dueno, None, estado=EstadoCancha.EN_MANTENIMIENTO)

        lecturas = [consulta['sql'] for consulta in capturadas.captured_queries if consulta['sql'].startswith('SELECT')]
        assert len([sql for sql in lecturas if '"reservas"' in sql]) == 1
        assert len([sql for sql in lecturas if '"turnos_fijos"' in sql]) == 1
        assert len([sql for sql in lecturas if '"horarios_apertura"' in sql]) == 1


class TestConflictoEnSql:
    """La agenda calcula la marca en SQL; tiene que coincidir siempre con la regla en Python."""

    @pytest.fixture
    def escenario(self, complejo, crear_cancha, crear_horario, crear_reserva):
        de_60 = crear_cancha(complejo, 'De 60')
        crear_horario(de_60, DiaSemana.MARTES, time(8, 0), time(12, 0))
        crear_horario(de_60, DiaSemana.MARTES, time(16, 0), time(23, 0))
        crear_horario(de_60, DiaSemana.LUNES, time(9, 0), time(13, 0))
        crear_horario(de_60, DiaSemana.MIERCOLES, time(8, 0), time(23, 0)).desactivar()
        de_90 = crear_cancha(complejo, 'De 90', duracion_turno_min=DuracionTurno.NOVENTA)
        crear_horario(de_90, DiaSemana.MARTES, time(14, 0), time(20, 0))
        de_120 = crear_cancha(complejo, 'De 120', duracion_turno_min=DuracionTurno.CIENTO_VEINTE)
        crear_horario(de_120, DiaSemana.MARTES, time(15, 30), time(23, 30))
        en_mantenimiento = crear_cancha(complejo, 'Mantenimiento', estado=EstadoCancha.EN_MANTENIMIENTO)
        crear_horario(en_mantenimiento, DiaSemana.MARTES, time(14, 0), time(23, 0))

        casos = [
            (de_60, MARTES, time(8, 0), time(9, 0)),
            (de_60, MARTES, time(11, 0), time(12, 0)),
            (de_60, MARTES, time(12, 0), time(13, 0)),
            (de_60, MARTES, time(8, 30), time(9, 30)),
            (de_60, MARTES, time(16, 0), time(17, 30)),
            (de_60, MARTES, time(22, 0), time(23, 0)),
            (de_60, MARTES + timedelta(days=1), time(9, 0), time(10, 0)),
            (de_60, MARTES + timedelta(days=4), time(9, 0), time(10, 0)),
            (de_60, HOY, time(9, 0), time(10, 0)),
            (de_60, HOY, time(11, 0), time(12, 0)),
            (de_60, HOY, time(12, 30), time(13, 30)),
            (de_90, MARTES, time(14, 0), time(15, 30)),
            (de_90, MARTES, time(15, 30), time(17, 0)),
            (de_90, MARTES, time(17, 0), time(18, 30)),
            (de_90, MARTES, time(18, 30), time(20, 0)),
            (de_90, MARTES, time(15, 0), time(16, 30)),
            (de_90, MARTES + timedelta(days=7), time(14, 0), time(15, 0)),
            (de_120, MARTES, time(15, 30), time(17, 30)),
            (de_120, MARTES, time(21, 30), time(23, 30)),
            (de_120, MARTES, time(16, 0), time(18, 0)),
            (en_mantenimiento, MARTES, time(14, 0), time(15, 0)),
        ]
        estados = [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA]
        reservas = [
            crear_reserva(cancha, fecha, inicio, fin, estado=estados[indice % 3], usuario=None)
            for indice, (cancha, fecha, inicio, fin) in enumerate(casos)
        ]
        reservas += [
            crear_reserva(de_60, MARTES, time(9, 30), time(10, 30), estado=estado, usuario=None)
            for estado in (EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.COMPLETADA, EstadoReserva.AUSENTE)
        ]
        reservas.append(crear_reserva(de_60, HOY - timedelta(days=7), time(8, 30), time(9, 30), usuario=None))
        return reservas

    def test_sql_y_python_coinciden_en_cada_caso(self, escenario):
        from core.models import Reserva
        from core.services import ConflictoOperatoriaService

        anotadas = {
            reserva.pk: reserva.motivo_conflicto
            for reserva in ConflictoOperatoriaService.anotar(Reserva.objects.select_related('cancha'))
        }
        en_python = {
            reserva.pk: ConflictoOperatoriaService.motivo_de_reserva(Reserva.objects.select_related('cancha').get(pk=reserva.pk))
            for reserva in escenario
        }

        assert anotadas == en_python
        assert set(en_python.values()) == {None, MOTIVO_FUERA_DE_LOS_TURNOS, MOTIVO_CANCHA_EN_MANTENIMIENTO}

    def test_el_filtro_no_crece_con_las_reservas(self, superadmin, crear_reserva, cliente_de, cancha, horario):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        api = cliente_de(superadmin)

        def _consultas():
            with CaptureQueriesContext(connection) as capturadas:
                assert api.get(URL_AGENDA, {'con_conflicto': 'true'}).status_code == status.HTTP_200_OK
            return len(capturadas)

        crear_reserva(cancha, MARTES, time(14, 30), time(15, 30), usuario=None)
        pocas = _consultas()
        for semana in range(1, 8):
            for hora in (14, 16, 18):
                crear_reserva(cancha, MARTES + timedelta(days=7 * semana), time(hora, 30), time(hora + 1, 30),
                              usuario=None)

        assert _consultas() == pocas
        assert api.get(URL_AGENDA, {'con_conflicto': 'true'}).json()['count'] == 22
