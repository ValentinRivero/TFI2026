from datetime import date, time, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

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
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
    TipoOcupacion,
)
from core.repositories import ReservaRepository
from core.services import DifusionGrillaService, _sumar_meses

URL = '/api/reservas/'
URL_MIAS = '/api/reservas/mias/'

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)
MIERCOLES = HOY + timedelta(days=2)
MARTES_SIGUIENTE = MARTES + timedelta(days=7)


def _url_cancelar(reserva):
    return f'{URL}{reserva.id}/cancelar/'


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    """Cancha de 60 minutos: martes de 14 a 18 al precio base y de 18 a 23 a precio diferenciado; hoy de 9 a 12."""
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(18, 0))
    crear_horario(cancha, DiaSemana.MARTES, time(18, 0), time(23, 0), precio=Decimal('45000.00'))
    crear_horario(cancha, DiaSemana.LUNES, time(9, 0), time(12, 0))
    return cancha


def _pedido(cancha, fecha=MARTES, hora='14:00', **extra):
    return {'cancha': cancha.id, 'fecha_turno': fecha.isoformat(), 'hora_inicio': hora, **extra}


@pytest.fixture
def reservar_web(reloj, jugador, cliente_de):
    def _reservar(cancha, fecha=MARTES, hora='14:00', usuario=None, **extra):
        return cliente_de(usuario or jugador).post(URL, _pedido(cancha, fecha, hora, **extra), format='json')

    return _reservar


class TestAltaDeReservaWeb:
    def test_el_jugador_reserva_un_turno_libre(self, reservar_web, jugador, complejo, cancha):
        respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['complejo'] == {'id': complejo.id, 'nombre': complejo.nombre}
        assert cuerpo['cancha'] == {'id': cancha.id, 'nombre': 'Cancha 1'}
        assert cuerpo['deporte'] == 'Fútbol 5'
        assert cuerpo['fecha_turno'] == MARTES.isoformat()
        assert (cuerpo['hora_inicio'], cuerpo['hora_fin']) == ('14:00:00', '15:00:00')
        assert cuerpo['precio_acordado'] == '38000.00'
        assert cuerpo['estado'] == EstadoReserva.PENDIENTE
        assert cuerpo['estado_nombre'] == 'Pendiente Seña'
        assert cuerpo['tipo_ocupacion'] == TipoOcupacion.WEB
        reserva = Reserva.objects.get()
        assert reserva.usuario == jugador and reserva.creado_por == jugador
        assert reserva.nombre_cliente_manual == '' and reserva.turno_fijo is None

    def test_no_expone_las_observaciones_del_complejo(self, reservar_web, cancha):
        cuerpo = reservar_web(cancha).json()

        assert 'observaciones' not in cuerpo
        assert 'creado_por' not in cuerpo

    def test_informa_hasta_cuando_se_puede_cancelar(self, reservar_web, complejo, cancha):
        complejo.horas_limite_cancelacion = 6
        complejo.save()

        cuerpo = reservar_web(cancha).json()

        assert cuerpo['cancelable_hasta'].startswith('2026-11-17T08:00:00')

    def test_usa_el_precio_diferenciado_del_rango(self, reservar_web, cancha):
        cuerpo = reservar_web(cancha, hora='19:00').json()

        assert (cuerpo['hora_fin'], cuerpo['precio_acordado']) == ('20:00:00', '45000.00')

    @pytest.mark.parametrize('duracion, hora, fin', [
        (DuracionTurno.NOVENTA, '15:30', '17:00:00'),
        (DuracionTurno.CIENTO_VEINTE, '16:00', '18:00:00'),
    ])
    def test_calcula_hora_fin_con_la_duracion_de_la_cancha(
        self, reservar_web, complejo, crear_cancha, crear_horario, duracion, hora, fin,
    ):
        cancha = crear_cancha(complejo, 'Cancha Larga', duracion_turno_min=duracion)
        crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(20, 0))

        respuesta = reservar_web(cancha, hora=hora)

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['hora_fin'] == fin

    def test_ignora_hora_fin_y_precio_enviados_por_el_cliente(self, reservar_web, cancha):
        respuesta = reservar_web(cancha, hora_fin='23:00', precio_acordado='1.00', estado=EstadoReserva.SENADA)

        reserva = Reserva.objects.get(id=respuesta.json()['id'])
        assert (reserva.hora_fin, reserva.precio_acordado) == (time(15, 0), Decimal('38000.00'))
        assert reserva.estado == EstadoReserva.PENDIENTE

    @pytest.mark.parametrize('fecha, hora', [
        (MARTES, '14:30'),
        (MARTES, '13:00'),
        (MARTES, '23:00'),
        (MIERCOLES, '14:00'),
    ], ids=['fuera-de-grilla', 'antes-de-abrir', 'al-cierre', 'dia-sin-horario'])
    def test_un_horario_que_no_es_un_bloque_de_la_grilla_responde_400(self, reservar_web, cancha, fecha, hora):
        respuesta = reservar_web(cancha, fecha=fecha, hora=hora)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_inicio' in respuesta.json()['detail']
        assert not Reserva.objects.exists()

    def test_un_resto_que_no_completa_un_turno_no_se_reserva(self, reservar_web, complejo, crear_cancha, crear_horario):
        cancha = crear_cancha(complejo, 'Cancha 90', duracion_turno_min=DuracionTurno.NOVENTA)
        crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(18, 0))

        assert reservar_web(cancha, hora='17:00').status_code == status.HTTP_400_BAD_REQUEST

    def test_un_rango_dado_de_baja_no_genera_turnos(self, reservar_web, cancha):
        cancha.horarios.filter(dia_semana=DiaSemana.MARTES, hora_apertura=time(14, 0)).get().desactivar()

        assert reservar_web(cancha).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize('fecha, hora', [
        (HOY - timedelta(days=1), '14:00'),
        (HOY, '09:00'),
        (HOY, '10:00'),
    ], ids=['ayer', 'hoy-ya-paso', 'hoy-recien-empezado'])
    def test_un_turno_pasado_o_ya_iniciado_responde_400(self, reservar_web, cancha, fecha, hora):
        respuesta = reservar_web(cancha, fecha=fecha, hora=hora)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_inicio' in respuesta.json()['detail']

    def test_un_turno_de_hoy_que_todavia_no_empezo_se_reserva(self, reservar_web, cancha):
        assert reservar_web(cancha, fecha=HOY, hora='11:00').status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize('estado_contrato', [
        EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA,
    ])
    def test_un_complejo_sin_contrato_activo_no_toma_reservas(self, reservar_web, complejo, cancha, estado_contrato):
        complejo.estado_contrato = estado_contrato
        complejo.save()

        respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cancha' in respuesta.json()['detail']

    def test_un_complejo_dado_de_baja_no_toma_reservas(self, reservar_web, complejo, cancha):
        complejo.desactivar()

        assert reservar_web(cancha).status_code == status.HTTP_400_BAD_REQUEST

    def test_una_cancha_en_mantenimiento_no_se_reserva(self, reservar_web, cancha):
        cancha.estado = EstadoCancha.EN_MANTENIMIENTO
        cancha.save()

        assert reservar_web(cancha).status_code == status.HTTP_400_BAD_REQUEST

    def test_una_cancha_dada_de_baja_responde_400(self, reservar_web, cancha):
        cancha.desactivar()

        respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cancha' in respuesta.json()['detail']

    def test_una_cancha_de_deporte_inactivo_no_se_reserva(self, reservar_web, cancha):
        cancha.deporte.desactivar()

        assert reservar_web(cancha).status_code == status.HTTP_400_BAD_REQUEST


class TestAnticipacionYLimiteDeAltas:
    def test_se_reserva_hasta_dos_meses_por_delante(self, reservar_web, cancha):
        # Hoy es el lunes 16/11/2026: el último día reservable es el 16/01/2027 y el último martes, el 12/01.
        assert reservar_web(cancha, fecha=date(2027, 1, 12)).status_code == status.HTTP_201_CREATED

    def test_mas_alla_de_dos_meses_responde_400(self, reservar_web, cancha):
        respuesta = reservar_web(cancha, fecha=date(2027, 1, 19))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail']['fecha_turno'] == (
            'Se reserva con hasta 2 meses de anticipación (hasta el 16/01/2027).'
        )

    @pytest.mark.parametrize('desde, esperado', [
        (date(2026, 11, 16), date(2027, 1, 16)),
        (date(2026, 12, 31), date(2027, 2, 28)),
        (date(2027, 12, 31), date(2028, 2, 29)),
        (date(2026, 10, 31), date(2026, 12, 31)),
    ])
    def test_la_anticipacion_se_cuenta_en_meses_calendario(self, desde, esperado):
        assert _sumar_meses(desde, 2) == esperado

    def test_limita_las_altas_por_cuenta(self, reservar_web, crear_usuario, cancha):
        for _ in range(20):
            assert reservar_web(cancha, hora='14:30').status_code == status.HTTP_400_BAD_REQUEST

        respuesta = reservar_web(cancha)
        otra = reservar_web(cancha, usuario=crear_usuario('otra.jugadora@talibre.test'))

        assert respuesta.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert otra.status_code == status.HTTP_201_CREATED

    def test_el_limite_no_frena_las_consultas_ni_las_cancelaciones(
        self, reservar_web, jugador, crear_reserva, cliente_de, cancha,
    ):
        reserva = crear_reserva(cancha, MARTES_SIGUIENTE, time(14, 0), time(15, 0))
        for _ in range(21):
            reservar_web(cancha, hora='14:30')
        api = cliente_de(jugador)

        assert api.get(URL_MIAS).status_code == status.HTTP_200_OK
        assert api.post(_url_cancelar(reserva)).status_code == status.HTTP_200_OK


class TestColisiones:
    @pytest.mark.parametrize('estado', [
        EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA, EstadoReserva.SENADA, EstadoReserva.COMPLETADA,
    ])
    def test_una_reserva_ocupante_del_mismo_turno_responde_409(self, reservar_web, crear_reserva, cancha, estado):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=estado)

        respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == 'El turno ya está reservado.'
        assert Reserva.objects.count() == 1

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE, EstadoReserva.BAJA,
    ])
    def test_una_reserva_no_ocupante_libera_el_turno(self, reservar_web, crear_reserva, cancha, estado):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=estado)

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize('hora', ['14:00', '15:00'])
    def test_una_superposicion_parcial_responde_409(self, reservar_web, crear_reserva, cancha, hora):
        crear_reserva(cancha, MARTES, time(14, 30), time(15, 30), usuario=None)

        assert reservar_web(cancha, hora=hora).status_code == status.HTTP_409_CONFLICT

    def test_una_reserva_contigua_no_choca(self, reservar_web, crear_reserva, cancha):
        crear_reserva(cancha, MARTES, time(15, 0), time(16, 0))

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED

    def test_ignora_reservas_de_otra_fecha_o_de_otra_cancha(
        self, reservar_web, crear_reserva, complejo, crear_cancha, cancha,
    ):
        crear_reserva(cancha, MARTES_SIGUIENTE, time(14, 0), time(15, 0))
        crear_reserva(crear_cancha(complejo, 'Cancha 2'), MARTES, time(14, 0), time(15, 0))

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED

    def test_el_segundo_jugador_del_mismo_turno_recibe_409(self, reservar_web, crear_usuario, cancha):
        otro = crear_usuario('otra.jugadora@talibre.test', nombre_completo='Otra Jugadora')

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED
        assert reservar_web(cancha, usuario=otro).status_code == status.HTTP_409_CONFLICT
        assert Reserva.objects.count() == 1

    def test_un_turno_fijo_vigente_responde_409(self, reservar_web, crear_turno_fijo, cancha):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=HOY)

        respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == 'El horario está tomado por un turno fijo.'

    @pytest.mark.parametrize('cambios', [
        {'estado': EstadoTurnoFijo.PAUSADO},
        {'estado': EstadoTurnoFijo.BAJA},
        {'fecha_inicio_vigencia': MARTES_SIGUIENTE},
        {'fecha_fin_vigencia': HOY},
        {'dia_semana': DiaSemana.MIERCOLES},
    ], ids=['pausado', 'baja', 'empieza-despues', 'termino-antes', 'otro-dia'])
    def test_un_turno_fijo_que_no_rige_esa_fecha_no_choca(self, reservar_web, crear_turno_fijo, cancha, cambios):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=HOY)
        for campo, valor in cambios.items():
            setattr(turno, campo, valor)
        turno.save()

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED

    def test_la_fecha_cancelada_de_un_turno_fijo_se_puede_reservar(
        self, reservar_web, crear_turno_fijo, crear_reserva, dueno, cancha,
    ):
        turno = crear_turno_fijo(cancha, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=HOY)
        crear_reserva(
            cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.CANCELADA_COMPLEJO, usuario=None,
            creado_por=dueno, turno_fijo=turno, tipo_ocupacion=TipoOcupacion.TURNO_FIJO,
        )

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED
        assert reservar_web(cancha, fecha=MARTES_SIGUIENTE).status_code == status.HTTP_409_CONFLICT

    def test_una_excepcion_global_de_dia_completo_responde_409(
        self, reservar_web, crear_excepcion_horaria, complejo, cancha,
    ):
        crear_excepcion_horaria(complejo, MARTES, tipo_motivo=TipoMotivoExcepcion.FERIADO)

        respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.json()['detail'] == 'La cancha está cerrada en ese horario por una excepción (Feriado).'

    def test_una_franja_de_la_cancha_superpuesta_responde_409(
        self, reservar_web, crear_excepcion_horaria, complejo, cancha,
    ):
        crear_excepcion_horaria(complejo, MARTES, cancha=cancha, inicio=time(14, 30), fin=time(16, 0))

        assert reservar_web(cancha, hora='15:00').status_code == status.HTTP_409_CONFLICT
        assert reservar_web(cancha, hora='16:00').status_code == status.HTTP_201_CREATED

    def test_una_excepcion_de_varios_dias_cubre_la_fecha(self, reservar_web, crear_excepcion_horaria, complejo, cancha):
        crear_excepcion_horaria(complejo, HOY, hasta=MIERCOLES)

        assert reservar_web(cancha).status_code == status.HTTP_409_CONFLICT

    def test_ignora_excepciones_de_otra_cancha_de_otra_fecha_o_dadas_de_baja(
        self, reservar_web, crear_excepcion_horaria, complejo, complejo_ajeno, crear_cancha, cancha,
    ):
        crear_excepcion_horaria(complejo, MARTES, cancha=crear_cancha(complejo, 'Cancha 2'))
        crear_excepcion_horaria(complejo, MIERCOLES)
        crear_excepcion_horaria(complejo, MARTES).desactivar()
        crear_excepcion_horaria(complejo_ajeno, MARTES)

        assert reservar_web(cancha).status_code == status.HTTP_201_CREATED

    def test_bloquea_la_cancha_antes_de_validar(self, reservar_web, cancha):
        with mock.patch.object(
            ReservaRepository, 'bloquear_cancha', wraps=ReservaRepository.bloquear_cancha,
        ) as bloquear:
            reservar_web(cancha)

        bloquear.assert_called_once_with(cancha.id)

    def test_la_restriccion_de_base_ante_un_alta_simultanea_responde_409(self, reservar_web, cancha):
        with mock.patch.object(ReservaRepository, 'crear', side_effect=IntegrityError('uq_reserva_cancha_turno_activa')):
            respuesta = reservar_web(cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert not Reserva.objects.exists()


class TestValidacionDeDatos:
    @pytest.mark.parametrize('campo, valor', [
        ('fecha_turno', '17/11/2026'),
        ('hora_inicio', 'catorce'),
        ('cancha', 99999),
    ])
    def test_datos_invalidos_responden_400(self, reloj, jugador, cliente_de, cancha, campo, valor):
        datos = _pedido(cancha)
        datos[campo] = valor

        respuesta = cliente_de(jugador).post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_faltan_campos_obligatorios(self, reloj, jugador, cliente_de, cancha):
        respuesta = cliente_de(jugador).post(URL, {}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert set(respuesta.json()['detail']) == {'cancha', 'fecha_turno', 'hora_inicio'}


class TestPermisosDeReserva:
    def test_sin_sesion_responde_401(self, cliente, cancha):
        assert cliente.post(URL, _pedido(cancha), format='json').status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize('rol', ['dueno', 'operador'])
    def test_el_personal_del_complejo_no_reserva_como_jugador(self, request, reloj, cliente_de, cancha, rol):
        usuario = request.getfixturevalue(rol)

        respuesta = cliente_de(usuario).post(URL, _pedido(cancha), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not Reserva.objects.exists()

    def test_el_superadmin_puede_reservar(self, reservar_web, superadmin, cancha):
        assert reservar_web(cancha, usuario=superadmin).status_code == status.HTTP_201_CREATED

    def test_sin_el_permiso_asignado_responde_403(self, reservar_web, cancha):
        from core.models import RolPermiso

        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='reservar_turno').desactivar()

        assert reservar_web(cancha).status_code == status.HTTP_403_FORBIDDEN

    def test_no_hay_listado_general_de_reservas(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestAuditoriaYDifusionDeReservas:
    def test_el_alta_se_audita_sin_datos_personales(self, reservar_web, jugador, complejo, cancha):
        reserva_id = reservar_web(cancha).json()['id']

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CREADA)
        assert log.usuario == jugador and log.complejo == complejo
        assert f'Reserva id {reserva_id}.' in log.detalle
        assert f'Cancha id {cancha.id}.' in log.detalle
        assert '2026-11-17 de 14:00 a 15:00' in log.detalle
        assert 'jugador@talibre.test' not in log.detalle
        assert 'Jugador Prueba' not in log.detalle

    def test_la_grilla_se_avisa_recien_al_confirmar(
        self, reservar_web, complejo, cancha, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks() as pendientes:
                reservar_web(cancha)
                publicar.assert_not_called()
            for callback in pendientes:
                callback()

        publicar.assert_called_once_with(complejo.id, {
            'event': 'grilla_actualizada',
            'cancha_id': cancha.id,
            'fecha_desde': MARTES.isoformat(),
            'fecha_hasta': MARTES.isoformat(),
            'hora_inicio': '14:00:00',
            'hora_fin': '15:00:00',
        })

    def test_un_rechazo_no_anuncia_nada(
        self, reservar_web, crear_reserva, cancha, django_capture_on_commit_callbacks,
    ):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        with django_capture_on_commit_callbacks() as pendientes:
            assert reservar_web(cancha).status_code == status.HTTP_409_CONFLICT

        assert pendientes == []


class TestMisReservas:
    def test_lista_solo_las_propias_paginadas(self, reloj, jugador, crear_usuario, crear_reserva, cliente_de, cancha):
        propia = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        otro = crear_usuario('otro.jugador@talibre.test')
        crear_reserva(cancha, MARTES, time(15, 0), time(16, 0), usuario=otro, creado_por=otro)
        crear_reserva(cancha, MARTES, time(16, 0), time(17, 0), usuario=None)

        cuerpo = cliente_de(jugador).get(URL_MIAS).json()

        assert set(cuerpo) == {'count', 'next', 'previous', 'results'}
        assert [reserva['id'] for reserva in cuerpo['results']] == [propia.id]

    def test_incluye_canceladas_y_excluye_la_baja_logica(self, reloj, jugador, crear_reserva, cliente_de, cancha):
        cancelada = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.CANCELADA_JUGADOR)
        crear_reserva(cancha, MARTES, time(15, 0), time(16, 0), estado=EstadoReserva.BAJA)

        resultados = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert [reserva['id'] for reserva in resultados] == [cancelada.id]

    def test_pagina_de_a_20(self, reloj, jugador, crear_reserva, cliente_de, cancha):
        for semana in range(21):
            crear_reserva(cancha, MARTES + timedelta(days=7 * semana), time(14, 0), time(15, 0))

        cuerpo = cliente_de(jugador).get(URL_MIAS).json()

        assert cuerpo['count'] == 21 and len(cuerpo['results']) == 20 and cuerpo['next'] is not None

    def test_ordena_por_fecha_y_hora(self, reloj, jugador, crear_reserva, cliente_de, cancha):
        tarde = crear_reserva(cancha, MARTES, time(16, 0), time(17, 0))
        temprano = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        siguiente = crear_reserva(cancha, MARTES_SIGUIENTE, time(14, 0), time(15, 0))

        api = cliente_de(jugador)
        ascendente = [r['id'] for r in api.get(URL_MIAS).json()['results']]
        descendente = [r['id'] for r in api.get(URL_MIAS, {'ordering': '-fecha_turno,-hora_inicio'}).json()['results']]

        assert ascendente == [temprano.id, tarde.id, siguiente.id]
        assert descendente == [siguiente.id, tarde.id, temprano.id]

    def test_un_turno_de_hoy_es_proximo_hasta_que_termina(self, reloj, jugador, crear_reserva, cliente_de, cancha):
        # El reloj marca las 10:00.
        terminada = crear_reserva(cancha, HOY, time(8, 0), time(9, 0), estado=EstadoReserva.COMPLETADA)
        justo_termina = crear_reserva(cancha, HOY, time(9, 0), time(10, 0))
        en_curso = crear_reserva(cancha, HOY, time(9, 30), time(10, 30), usuario=jugador, creado_por=jugador)
        por_empezar = crear_reserva(cancha, HOY, time(11, 0), time(12, 0))

        api = cliente_de(jugador)
        proximas = {r['id'] for r in api.get(URL_MIAS, {'vigencia': 'proximas'}).json()['results']}
        pasadas = {r['id'] for r in api.get(URL_MIAS, {'vigencia': 'pasadas'}).json()['results']}

        assert proximas == {en_curso.id, por_empezar.id}
        assert pasadas == {terminada.id, justo_termina.id}

    def test_filtra_por_vigencia(self, reloj, jugador, crear_reserva, cliente_de, cancha):
        pasada = crear_reserva(cancha, HOY - timedelta(days=6), time(14, 0), time(15, 0), estado=EstadoReserva.COMPLETADA)
        proxima = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        api = cliente_de(jugador)

        assert [r['id'] for r in api.get(URL_MIAS, {'vigencia': 'proximas'}).json()['results']] == [proxima.id]
        assert [r['id'] for r in api.get(URL_MIAS, {'vigencia': 'pasadas'}).json()['results']] == [pasada.id]

    def test_filtra_por_estado_y_rango_de_fechas(self, reloj, jugador, crear_reserva, cliente_de, cancha):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE)
        senada = crear_reserva(cancha, MARTES_SIGUIENTE, time(14, 0), time(15, 0), estado=EstadoReserva.SENADA)

        api = cliente_de(jugador)
        por_estado = api.get(URL_MIAS, {'estado': EstadoReserva.SENADA}).json()['results']
        por_rango = api.get(URL_MIAS, {'fecha_desde': '2026-11-20', 'fecha_hasta': '2026-11-30'}).json()['results']

        assert [r['id'] for r in por_estado] == [senada.id]
        assert [r['id'] for r in por_rango] == [senada.id]

    @pytest.mark.parametrize('parametros', [
        {'estado': EstadoReserva.BAJA},
        {'vigencia': 'todas'},
        {'fecha_desde': '20/11/2026'},
    ])
    def test_filtros_invalidos_responden_400(self, reloj, jugador, cliente_de, parametros):
        assert cliente_de(jugador).get(URL_MIAS, parametros).status_code == status.HTTP_400_BAD_REQUEST

    def test_sin_sesion_responde_401(self, cliente):
        assert cliente.get(URL_MIAS).status_code == status.HTTP_401_UNAUTHORIZED

    def test_la_cantidad_de_consultas_no_crece_con_las_reservas(
        self, reloj, jugador, crear_reserva, cliente_de, complejo_ajeno, crear_cancha, cancha,
    ):
        api = cliente_de(jugador)

        def _consultas():
            with CaptureQueriesContext(connection) as capturadas:
                assert api.get(URL_MIAS).status_code == status.HTTP_200_OK
            return len(capturadas)

        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        pocas = _consultas()
        otra_cancha = crear_cancha(complejo_ajeno, 'Pádel 1', deporte='Pádel')
        for hora in range(15, 20):
            crear_reserva(otra_cancha, MARTES, time(hora, 0), time(hora + 1, 0))

        assert _consultas() == pocas

    def test_el_personal_del_complejo_recibe_403(self, operador, cliente_de):
        assert cliente_de(operador).get(URL_MIAS).status_code == status.HTTP_403_FORBIDDEN


class TestCancelacionPorElJugador:
    @pytest.fixture
    def reserva(self, crear_reserva, cancha):
        """Turno del martes a las 14:00: el reloj marca el lunes a las 10:00, faltan 28 horas."""
        return crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.CONFIRMADA)

    def _cancelar(self, cliente_de, usuario, reserva):
        return cliente_de(usuario).post(_url_cancelar(reserva))

    def test_cancela_dentro_del_margen(self, reloj, jugador, cliente_de, reserva):
        respuesta = self._cancelar(cliente_de, jugador, reserva)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoReserva.CANCELADA_JUGADOR
        reserva.refresh_from_db()
        assert reserva.estado == EstadoReserva.CANCELADA_JUGADOR

    def test_al_cancelar_el_turno_queda_libre(self, reloj, jugador, crear_usuario, cliente_de, reserva, cancha):
        self._cancelar(cliente_de, jugador, reserva)
        otro = crear_usuario('otra.jugadora@talibre.test')

        assert cliente_de(otro).post(URL, _pedido(cancha), format='json').status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize('estado', [EstadoReserva.PENDIENTE, EstadoReserva.SENADA])
    def test_tambien_cancela_pendientes_y_senadas(self, reloj, jugador, cliente_de, reserva, estado):
        reserva.estado = estado
        reserva.save()

        assert self._cancelar(cliente_de, jugador, reserva).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('horas_antes, esperado', [
        (5, status.HTTP_200_OK),
        (4, status.HTTP_400_BAD_REQUEST),
        (3, status.HTTP_400_BAD_REQUEST),
    ], ids=['con-margen', 'justo-en-el-limite', 'sin-margen'])
    def test_exige_que_falten_mas_horas_que_el_limite(
        self, reloj, jugador, cliente_de, reserva, horas_antes, esperado,
    ):
        inicio = reloj.return_value.replace(day=17, hour=14)
        reloj.return_value = inicio - timedelta(hours=horas_antes)

        respuesta = self._cancelar(cliente_de, jugador, reserva)

        assert respuesta.status_code == esperado
        reserva.refresh_from_db()
        cancelada = reserva.estado == EstadoReserva.CANCELADA_JUGADOR
        assert cancelada is (esperado == status.HTTP_200_OK)

    def test_el_mensaje_informa_el_margen(self, reloj, jugador, cliente_de, complejo, reserva):
        complejo.horas_limite_cancelacion = 1
        complejo.save()
        reloj.return_value = reloj.return_value.replace(day=17, hour=13, minute=30)

        respuesta = self._cancelar(cliente_de, jugador, reserva)

        assert respuesta.json()['detail'] == (
            'Solo podés cancelar con más de 1 hora de anticipación. Comunicate con el complejo.'
        )

    def test_respeta_el_margen_configurado_por_el_complejo(self, reloj, jugador, cliente_de, complejo, reserva):
        complejo.horas_limite_cancelacion = 48
        complejo.save()

        respuesta = self._cancelar(cliente_de, jugador, reserva)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert '48 horas' in respuesta.json()['detail']

    def test_sin_margen_configurado_cancela_hasta_el_inicio(self, reloj, jugador, cliente_de, complejo, reserva):
        complejo.horas_limite_cancelacion = 0
        complejo.save()
        reloj.return_value = reloj.return_value.replace(day=17, hour=13, minute=59)

        assert self._cancelar(cliente_de, jugador, reserva).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('hora', [14, 16])
    def test_un_turno_iniciado_o_pasado_no_se_cancela(self, reloj, jugador, cliente_de, complejo, reserva, hora):
        complejo.horas_limite_cancelacion = 0
        complejo.save()
        reloj.return_value = reloj.return_value.replace(day=17, hour=hora)

        respuesta = self._cancelar(cliente_de, jugador, reserva)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail'] == 'El turno ya comenzó: no se puede cancelar.'

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE,
        EstadoReserva.COMPLETADA,
    ])
    def test_una_reserva_cerrada_no_se_cancela(self, reloj, jugador, cliente_de, reserva, estado):
        reserva.estado = estado
        reserva.save()

        assert self._cancelar(cliente_de, jugador, reserva).status_code == status.HTTP_400_BAD_REQUEST

    def test_una_reserva_ajena_responde_404(self, reloj, crear_usuario, cliente_de, reserva):
        otro = crear_usuario('otro.jugador@talibre.test')

        assert self._cancelar(cliente_de, otro, reserva).status_code == status.HTTP_404_NOT_FOUND
        reserva.refresh_from_db()
        assert reserva.estado == EstadoReserva.CONFIRMADA

    def test_una_reserva_dada_de_baja_o_inexistente_responde_404(self, reloj, jugador, cliente_de, reserva):
        reserva.estado = EstadoReserva.BAJA
        reserva.save()

        assert self._cancelar(cliente_de, jugador, reserva).status_code == status.HTTP_404_NOT_FOUND
        assert cliente_de(jugador).post(f'{URL}99999/cancelar/').status_code == status.HTTP_404_NOT_FOUND

    def test_el_personal_del_complejo_no_usa_esta_ruta(self, reloj, operador, cliente_de, reserva):
        assert self._cancelar(cliente_de, operador, reserva).status_code == status.HTTP_403_FORBIDDEN

    def test_la_cancelacion_se_audita_y_se_anuncia(
        self, reloj, jugador, cliente_de, complejo, reserva, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                self._cancelar(cliente_de, jugador, reserva)

        publicar.assert_called_once()
        assert publicar.call_args.args[0] == complejo.id
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CANCELADA)
        assert log.usuario == jugador
        assert 'Confirmada -> Cancelada por el jugador.' in log.detalle

    def test_un_rechazo_no_se_audita(self, reloj, jugador, cliente_de, complejo, reserva):
        complejo.horas_limite_cancelacion = 48
        complejo.save()

        self._cancelar(cliente_de, jugador, reserva)

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.RESERVA_CANCELADA).exists()
