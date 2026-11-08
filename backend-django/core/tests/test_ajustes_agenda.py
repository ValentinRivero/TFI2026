from datetime import time, timedelta
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import (
    DiaSemana,
    EstadoCancha,
    EstadoContrato,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    LogAuditoria,
    Reserva,
    RolPermiso,
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
    TipoOcupacion,
)
from core.services import PRIORIDAD_AVISO_URGENTE, AvisoComplejoService, DifusionGrillaService

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)


def _martes(semanas):
    return MARTES + timedelta(days=7 * semanas)


@pytest.fixture(autouse=True)
def lunes_a_las_diez(reloj):
    return reloj


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def cancelada(crear_reserva, cancha):
    return crear_reserva(cancha, MARTES, time(20, 0), time(21, 0), estado=EstadoReserva.CANCELADA_COMPLEJO)


def _reabrir(api, reserva, **datos):
    return api.post(f'/api/agenda/{reserva.id}/reabrir/', datos, format='json')


class TestReaperturaDeReservas:
    def test_sin_confirmar_muestra_la_vista_previa_y_no_cambia_nada(self, operador, cliente_de, cancelada):
        respuesta = _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        cuerpo = respuesta.json()
        assert cuerpo['requiere_confirmacion'] is True and '"confirmar": true' in cuerpo['detail']
        assert cuerpo['vista_previa'] == {
            'id': cancelada.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '20:00:00', 'hora_fin': '21:00:00',
            'estado_actual': EstadoReserva.CANCELADA_COMPLEJO, 'estado_nuevo': EstadoReserva.CONFIRMADA,
        }
        cancelada.refresh_from_db()
        assert cancelada.estado == EstadoReserva.CANCELADA_COMPLEJO

    @pytest.mark.parametrize('estado_cancelado', [EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO])
    @pytest.mark.parametrize('estado_nuevo', [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA])
    def test_con_confirmar_vuelve_al_estado_elegido(
        self, operador, cliente_de, cancelada, estado_cancelado, estado_nuevo,
    ):
        cancelada.estado = estado_cancelado
        cancelada.save()

        respuesta = _reabrir(cliente_de(operador), cancelada, estado=estado_nuevo, confirmar=True)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == estado_nuevo
        cancelada.refresh_from_db()
        assert cancelada.estado == estado_nuevo

    def test_vuelve_a_ocupar_el_turno(self, cliente, operador, cliente_de, complejo, cancelada):
        _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA, confirmar=True)

        grilla = cliente.get(f'/api/complejos/{complejo.id}/grilla/?fecha={MARTES.isoformat()}').json()
        estados = {b['hora_inicio']: b['estado'] for b in grilla['canchas'][0]['bloques']}

        assert estados['20:00:00'] == 'OCUPADO'

    def test_si_otra_reserva_tomo_el_turno_es_un_choque_que_no_se_confirma(
        self, operador, crear_reserva, cliente_de, cancha, cancelada,
    ):
        crear_reserva(cancha, MARTES, time(20, 0), time(21, 0), usuario=None)

        respuesta = _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA, confirmar=True)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert 'requiere_confirmacion' not in respuesta.json()
        assert respuesta.json()['detail'] == 'El turno ya está reservado.'

    def test_si_una_excepcion_cerro_el_turno_es_un_choque(
        self, operador, crear_excepcion_horaria, cliente_de, complejo, cancelada,
    ):
        crear_excepcion_horaria(complejo, MARTES, tipo_motivo=TipoMotivoExcepcion.FERIADO)

        respuesta = _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert 'requiere_confirmacion' not in respuesta.json()

    def test_si_un_turno_fijo_tomo_el_horario_es_un_choque(
        self, operador, crear_turno_fijo, cliente_de, cancha, cancelada,
    ):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(20, 0), time(21, 0), desde=HOY)

        respuesta = _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA)

        assert respuesta.json()['detail'] == 'El horario está tomado por un turno fijo.'

    def test_si_cambio_el_horario_de_la_cancha_es_un_choque(self, operador, cliente_de, cancha, cancelada):
        cancha.horarios.update(hora_cierre=time(19, 0))

        respuesta = _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == 'El turno ya no coincide con los horarios vigentes de la cancha.'

    @pytest.mark.parametrize('cambio', ['mantenimiento', 'contrato'])
    def test_si_la_cancha_o_el_complejo_no_estan_disponibles_es_un_choque(
        self, operador, cliente_de, complejo, cancha, cancelada, cambio,
    ):
        if cambio == 'mantenimiento':
            cancha.estado = EstadoCancha.EN_MANTENIMIENTO
            cancha.save()
        else:
            complejo.estado_contrato = EstadoContrato.SUSPENDIDO
            complejo.save()

        assert _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA).status_code == 409

    def test_reabre_la_fecha_cancelada_de_un_turno_fijo(
        self, operador, crear_turno_fijo, crear_reserva, cliente_de, cancha,
    ):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=HOY)
        fecha = crear_reserva(
            cancha, MARTES, time(21, 0), time(22, 0), usuario=None, turno_fijo=turno,
            tipo_ocupacion=TipoOcupacion.TURNO_FIJO, estado=EstadoReserva.CANCELADA_COMPLEJO,
        )

        respuesta = _reabrir(cliente_de(operador), fecha, estado=EstadoReserva.CONFIRMADA, confirmar=True)

        assert respuesta.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('estado', [
        EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA, EstadoReserva.AUSENTE,
        EstadoReserva.COMPLETADA,
    ])
    def test_solo_se_reabre_una_reserva_cancelada(self, operador, cliente_de, cancelada, estado):
        cancelada.estado = estado
        cancelada.save()

        assert _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA).status_code == 400

    def test_un_turno_ya_iniciado_no_se_reabre(self, reloj, operador, cliente_de, cancelada):
        reloj.return_value = reloj.return_value.replace(day=17, hour=20, minute=10)

        respuesta = _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_la_reserva_de_una_cuenta_dada_de_baja_no_se_reabre(self, operador, jugador, cliente_de, cancelada):
        jugador.estado = EstadoUsuario.BAJA
        jugador.save()

        assert _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA).status_code == 400

    @pytest.mark.parametrize('estado', [EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.AUSENTE, 0, 9])
    def test_el_estado_nuevo_debe_ser_pendiente_confirmada_o_senada(self, operador, cliente_de, cancelada, estado):
        respuesta = _reabrir(cliente_de(operador), cancelada, estado=estado)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado' in respuesta.json()['detail']

    def test_el_jugador_no_reabre_reservas(self, jugador, cliente_de, cancelada):
        assert _reabrir(cliente_de(jugador), cancelada, estado=EstadoReserva.CONFIRMADA).status_code == 403

    def test_sin_gestionar_agenda_responde_403(self, operador, cliente_de, cancelada):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='gestionar_agenda').desactivar()

        assert _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA).status_code == 403

    def test_una_reserva_ajena_responde_404(self, dueno, crear_reserva, complejo_ajeno, crear_cancha, cliente_de):
        ajena = crear_reserva(crear_cancha(complejo_ajeno, 'Ajena'), MARTES, time(20, 0), time(21, 0),
                              estado=EstadoReserva.CANCELADA_COMPLEJO)

        assert _reabrir(cliente_de(dueno), ajena, estado=EstadoReserva.CONFIRMADA).status_code == 404

    def test_se_audita_y_se_anuncia(
        self, operador, complejo, cliente_de, cancelada, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.SENADA, confirmar=True)

        publicar.assert_called_once()
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO)
        assert log.accion == 'Reapertura de reserva cancelada'
        assert 'Cancelada por el complejo -> Señada/Pagada.' in log.detalle

    def test_la_vista_previa_no_audita_ni_anuncia(
        self, operador, cliente_de, cancelada, django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks() as pendientes:
            _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA)

        assert pendientes == []
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO).exists()


class TestCambioDeHorarioDeTurnoFijo:
    @pytest.fixture
    def turno(self, crear_turno_fijo, cancha):
        return crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES)

    def _patch(self, api, turno, **datos):
        return api.patch(f'/api/turnos-fijos/{turno.id}/', datos, format='json')

    def test_sin_confirmar_muestra_la_vista_previa(self, dueno, crear_reserva, cliente_de, cancha, turno):
        registrada = crear_reserva(
            cancha, _martes(1), time(21, 0), time(22, 0), usuario=None, turno_fijo=turno,
            tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
        )

        respuesta = self._patch(cliente_de(dueno), turno, hora_inicio='19:00')

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        cuerpo = respuesta.json()
        assert cuerpo['requiere_confirmacion'] is True
        assert cuerpo['vista_previa'] == {
            'horario_actual': {'hora_inicio': '21:00:00', 'hora_fin': '22:00:00'},
            'horario_nuevo': {'hora_inicio': '19:00:00', 'hora_fin': '20:00:00'},
            'rige_desde': MARTES.isoformat(),
            'fechas_registradas': [
                {'id': registrada.id, 'fecha_turno': _martes(1).isoformat(), 'estado': EstadoReserva.CONFIRMADA},
            ],
        }
        turno.refresh_from_db()
        assert turno.hora_inicio == time(21, 0)

    def test_con_confirmar_cambia_el_horario_y_recalcula_el_fin(self, dueno, cliente_de, turno):
        respuesta = self._patch(cliente_de(dueno), turno, hora_inicio='19:00', confirmar=True)

        assert respuesta.status_code == status.HTTP_200_OK
        assert (respuesta.json()['hora_inicio'], respuesta.json()['hora_fin']) == ('19:00:00', '20:00:00')

    def test_libera_el_horario_viejo_y_ocupa_el_nuevo(self, dueno, jugador, cliente_de, cancha, turno):
        self._patch(cliente_de(dueno), turno, hora_inicio='19:00', confirmar=True)
        api = cliente_de(jugador)

        def reservar(hora):
            return api.post('/api/reservas/', {
                'cancha': cancha.id, 'fecha_turno': _martes(1).isoformat(), 'hora_inicio': hora,
            }, format='json').status_code

        assert reservar('21:00') == status.HTTP_201_CREATED
        assert reservar('19:00') == status.HTTP_409_CONFLICT

    def test_las_fechas_ya_registradas_conservan_el_horario_anterior(
        self, dueno, crear_reserva, cliente_de, cancha, turno,
    ):
        registrada = crear_reserva(
            cancha, _martes(1), time(21, 0), time(22, 0), usuario=None, turno_fijo=turno,
            tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
        )

        self._patch(cliente_de(dueno), turno, hora_inicio='19:00', confirmar=True)

        registrada.refresh_from_db()
        assert (registrada.hora_inicio, registrada.estado) == (time(21, 0), EstadoReserva.CONFIRMADA)

    def test_un_horario_que_no_es_turno_de_la_grilla_responde_400(self, dueno, cliente_de, turno):
        for hora in ('19:30', '23:00', '10:00'):
            respuesta = self._patch(cliente_de(dueno), turno, hora_inicio=hora, confirmar=True)
            assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
            assert 'hora_inicio' in respuesta.json()['detail']

    def test_choca_con_otro_turno_fijo_o_una_reserva_y_no_se_confirma(
        self, dueno, crear_turno_fijo, crear_reserva, cliente_de, cancha, turno,
    ):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(19, 0), time(20, 0), desde=MARTES)
        crear_reserva(cancha, _martes(2), time(18, 0), time(19, 0))
        api = cliente_de(dueno)

        al_turno = self._patch(api, turno, hora_inicio='19:00', confirmar=True)
        a_la_reserva = self._patch(api, turno, hora_inicio='18:00', confirmar=True)

        for respuesta in (al_turno, a_la_reserva):
            assert respuesta.status_code == status.HTTP_409_CONFLICT
            assert 'requiere_confirmacion' not in respuesta.json()

    def test_una_excepcion_no_impide_el_cambio(self, dueno, crear_excepcion_horaria, cliente_de, complejo, turno):
        crear_excepcion_horaria(complejo, _martes(2), tipo_motivo=TipoMotivoExcepcion.FERIADO)

        respuesta = self._patch(cliente_de(dueno), turno, hora_inicio='19:00', confirmar=True)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['fechas_en_espera'] == [{'fecha': _martes(2).isoformat(), 'motivo': 'Feriado'}]

    def test_un_turno_pausado_cambia_de_horario_sin_revisar_choques(
        self, dueno, crear_turno_fijo, cliente_de, cancha, turno,
    ):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(19, 0), time(20, 0), desde=MARTES)
        turno.estado = EstadoTurnoFijo.PAUSADO
        turno.save()
        api = cliente_de(dueno)

        cambio = self._patch(api, turno, hora_inicio='19:00', confirmar=True)
        reanudar = self._patch(api, turno, estado=EstadoTurnoFijo.VIGENTE)

        assert cambio.status_code == status.HTTP_200_OK
        assert reanudar.status_code == status.HTTP_409_CONFLICT

    def test_el_jugador_no_cambia_horarios(self, jugador, cliente_de, turno):
        assert self._patch(cliente_de(jugador), turno, hora_inicio='19:00', confirmar=True).status_code == 403

    def test_el_cambio_se_anuncia_para_el_dia_completo(
        self, dueno, cliente_de, complejo, cancha, turno, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                self._patch(cliente_de(dueno), turno, hora_inicio='19:00', confirmar=True)

        publicar.assert_called_once_with(complejo.id, {
            'event': 'grilla_actualizada', 'cancha_id': cancha.id, 'fecha_desde': MARTES.isoformat(),
            'fecha_hasta': None, 'hora_inicio': None, 'hora_fin': None,
        })


class TestFechasEnEspera:
    @pytest.fixture
    def turno(self, crear_turno_fijo, cancha):
        return crear_turno_fijo(cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES)

    @pytest.fixture
    def feriado(self, crear_excepcion_horaria, complejo):
        return crear_excepcion_horaria(complejo, _martes(2), tipo_motivo=TipoMotivoExcepcion.FERIADO)

    def _listado(self, api, **parametros):
        return {item['id']: item for item in api.get('/api/turnos-fijos/', parametros).json()['results']}

    def test_una_excepcion_posterior_deja_la_fecha_en_espera(self, operador, cliente_de, turno, feriado):
        listado = self._listado(cliente_de(operador))

        assert listado[turno.id]['fechas_en_espera'] == [{'fecha': _martes(2).isoformat(), 'motivo': 'Feriado'}]

    def test_el_detalle_tambien_las_informa(self, operador, cliente_de, turno, feriado):
        detalle = cliente_de(operador).get(f'/api/turnos-fijos/{turno.id}/').json()

        assert [item['fecha'] for item in detalle['fechas_en_espera']] == [_martes(2).isoformat()]

    def test_una_excepcion_de_varias_semanas_deja_cada_martes_en_espera(
        self, operador, crear_excepcion_horaria, cliente_de, complejo, cancha, turno,
    ):
        crear_excepcion_horaria(
            complejo, _martes(1), hasta=_martes(3), cancha=cancha, inicio=time(20, 0), fin=time(23, 0),
            tipo_motivo=TipoMotivoExcepcion.MANTENIMIENTO,
        )

        fechas = self._listado(cliente_de(operador))[turno.id]['fechas_en_espera']

        assert fechas == [
            {'fecha': _martes(semana).isoformat(), 'motivo': 'Mantenimiento'} for semana in (1, 2, 3)
        ]

    def test_ignora_excepciones_que_no_la_alcanzan(
        self, operador, crear_excepcion_horaria, crear_cancha, cliente_de, complejo, complejo_ajeno, cancha, turno,
    ):
        crear_excepcion_horaria(complejo, _martes(1), cancha=cancha, inicio=time(14, 0), fin=time(21, 0))
        crear_excepcion_horaria(complejo, _martes(1), cancha=crear_cancha(complejo, 'Cancha 2'))
        crear_excepcion_horaria(complejo, _martes(1) + timedelta(days=1))
        crear_excepcion_horaria(complejo, _martes(1)).desactivar()
        crear_excepcion_horaria(complejo_ajeno, _martes(1))
        crear_excepcion_horaria(complejo, HOY - timedelta(days=6))

        assert self._listado(cliente_de(operador))[turno.id]['fechas_en_espera'] == []

    def test_una_fecha_fuera_de_la_vigencia_no_queda_en_espera(
        self, operador, crear_turno_fijo, cliente_de, cancha, feriado,
    ):
        corto = crear_turno_fijo(cancha, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=MARTES, hasta=_martes(1))

        assert self._listado(cliente_de(operador))[corto.id]['fechas_en_espera'] == []

    def test_un_turno_pausado_no_tiene_fechas_en_espera(self, operador, cliente_de, turno, feriado):
        turno.estado = EstadoTurnoFijo.PAUSADO
        turno.save()

        assert self._listado(cliente_de(operador))[turno.id]['fechas_en_espera'] == []

    def test_mientras_espera_sigue_ocupando_la_grilla(self, cliente, jugador, cliente_de, complejo, cancha, turno, feriado):
        grilla = cliente.get(f'/api/complejos/{complejo.id}/grilla/?fecha={_martes(2).isoformat()}').json()
        estados = {b['hora_inicio']: b['estado'] for b in grilla['canchas'][0]['bloques']}
        reserva = cliente_de(jugador).post('/api/reservas/', {
            'cancha': cancha.id, 'fecha_turno': _martes(2).isoformat(), 'hora_inicio': '21:00',
        }, format='json')

        assert estados['21:00:00'] == 'OCUPADO'
        assert estados['20:00:00'] == 'CERRADO_EXCEPCION'
        assert reserva.status_code == status.HTTP_409_CONFLICT

    def test_mantener_la_fecha_la_registra_confirmada_y_sale_de_espera(self, operador, cliente_de, turno, feriado):
        api = cliente_de(operador)

        respuesta = api.post(f'/api/turnos-fijos/{turno.id}/fechas/', {
            'fecha_turno': _martes(2).isoformat(), 'accion': 'mantener',
        }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['estado'] == EstadoReserva.CONFIRMADA
        assert self._listado(api)[turno.id]['fechas_en_espera'] == []

    def test_cancelar_la_fecha_la_registra_cancelada_y_el_cierre_vuelve_a_mandar(
        self, cliente, operador, cliente_de, complejo, turno, feriado,
    ):
        api = cliente_de(operador)

        respuesta = api.post(f'/api/turnos-fijos/{turno.id}/fechas/', {
            'fecha_turno': _martes(2).isoformat(), 'accion': 'cancelar',
        }, format='json')
        grilla = cliente.get(f'/api/complejos/{complejo.id}/grilla/?fecha={_martes(2).isoformat()}').json()
        estados = {b['hora_inicio']: b['estado'] for b in grilla['canchas'][0]['bloques']}

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['estado'] == EstadoReserva.CANCELADA_COMPLEJO
        assert self._listado(api)[turno.id]['fechas_en_espera'] == []
        assert estados['21:00:00'] == 'CERRADO_EXCEPCION'
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CANCELADA)
        assert log.accion == 'Fecha de turno fijo cancelada por el complejo'

    def test_cancelar_una_fecha_sin_excepcion_libera_el_casillero(self, operador, jugador, cliente_de, cancha, turno):
        cliente_de(operador).post(f'/api/turnos-fijos/{turno.id}/fechas/', {
            'fecha_turno': _martes(1).isoformat(), 'accion': 'cancelar',
        }, format='json')

        reserva = cliente_de(jugador).post('/api/reservas/', {
            'cancha': cancha.id, 'fecha_turno': _martes(1).isoformat(), 'hora_inicio': '21:00',
        }, format='json')

        assert reserva.status_code == status.HTTP_201_CREATED

    def test_una_accion_desconocida_responde_400(self, operador, cliente_de, turno):
        respuesta = cliente_de(operador).post(f'/api/turnos-fijos/{turno.id}/fechas/', {
            'fecha_turno': _martes(1).isoformat(), 'accion': 'posponer',
        }, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'accion' in respuesta.json()['detail']

    def test_filtra_los_turnos_fijos_con_fechas_en_espera(
        self, operador, crear_turno_fijo, cliente_de, cancha, turno, feriado,
    ):
        otro = crear_turno_fijo(cancha, DiaSemana.MIERCOLES, time(21, 0), time(22, 0), desde=MARTES)
        api = cliente_de(operador)

        assert list(self._listado(api, en_espera='true')) == [turno.id]
        assert list(self._listado(api, en_espera='false')) == [otro.id]

    def test_el_listado_no_hace_una_consulta_por_turno_fijo(
        self, operador, crear_turno_fijo, cliente_de, complejo, crear_cancha, cancha, turno, feriado,
    ):
        api = cliente_de(operador)

        def _consultas():
            with CaptureQueriesContext(connection) as capturadas:
                assert api.get('/api/turnos-fijos/').status_code == status.HTTP_200_OK
            return len(capturadas)

        pocas = _consultas()
        for numero in range(4):
            otra = crear_cancha(complejo, f'Cancha {numero + 2}')
            crear_turno_fijo(otra, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES)

        assert _consultas() == pocas

    def test_crear_una_excepcion_que_deja_fechas_en_espera_avisa_con_urgencia(
        self, dueno, cliente_de, complejo, turno, django_capture_on_commit_callbacks,
    ):
        datos = {
            'complejo': complejo.id, 'cancha': None, 'fecha_inicio': _martes(1).isoformat(),
            'fecha_fin': _martes(2).isoformat(), 'es_dia_completo': 1, 'tipo_motivo': TipoMotivoExcepcion.FERIADO,
            'descripcion': 'Aviso de Teodoro Arrúa',
        }

        with mock.patch.object(AvisoComplejoService, 'entregar') as entregar:
            with django_capture_on_commit_callbacks(execute=True):
                respuesta = cliente_de(dueno).post('/api/excepciones/', datos, format='json')

        (aviso,) = [llamada.args[0] for llamada in entregar.call_args_list]
        assert aviso['prioridad'] == PRIORIDAD_AVISO_URGENTE and aviso['complejo_id'] == complejo.id
        assert aviso['referencias'] == {'excepcion': respuesta.json()['id'], 'turnos_fijos': [turno.id]}
        assert '2 fechas' in aviso['mensaje'] and 'Teodoro' not in aviso['mensaje']

    def test_una_excepcion_que_no_alcanza_turnos_fijos_no_avisa(
        self, dueno, cliente_de, complejo, turno, django_capture_on_commit_callbacks,
    ):
        datos = {
            'complejo': complejo.id, 'cancha': None, 'fecha_inicio': _martes(1).isoformat(),
            'fecha_fin': _martes(1).isoformat(), 'es_dia_completo': 0, 'hora_inicio': '14:00', 'hora_fin': '16:00',
            'tipo_motivo': TipoMotivoExcepcion.MANTENIMIENTO,
        }

        with mock.patch.object(AvisoComplejoService, 'entregar') as entregar:
            with django_capture_on_commit_callbacks(execute=True):
                cliente_de(dueno).post('/api/excepciones/', datos, format='json')

        entregar.assert_not_called()


def test_la_reapertura_no_crea_otra_reserva(operador, cliente_de, cancelada):
    _reabrir(cliente_de(operador), cancelada, estado=EstadoReserva.CONFIRMADA, confirmar=True)

    assert Reserva.objects.count() == 1


def test_una_reserva_dada_de_baja_al_bloquear_responde_404(operador, cancelada):
    from rest_framework.exceptions import NotFound

    from core.services import ReservaService

    cancelada.estado = EstadoReserva.BAJA
    cancelada.save()

    with pytest.raises(NotFound):
        ReservaService.reabrir(cancelada, EstadoReserva.CONFIRMADA, True, operador, None)
