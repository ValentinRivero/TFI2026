from datetime import date, time, timedelta
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.exceptions import NotFound

from conftest import HOY_CONGELADO
from core.models import (
    DiaSemana,
    EstadoReserva,
    LogAuditoria,
    Reserva,
    RolPermiso,
    TipoEventoAuditoria,
    TipoOcupacion,
)
from core.services import DifusionGrillaService, ReservaService

URL = '/api/agenda/'

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)


def _url(reserva, accion=''):
    return f'{URL}{reserva.id}/{accion}'


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    """Cancha de 60 minutos abierta el martes de 14 a 23 y hoy, lunes, de 9 a 12."""
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    crear_horario(cancha, DiaSemana.LUNES, time(9, 0), time(12, 0))
    return cancha


@pytest.fixture
def cancha_ajena(complejo_ajeno, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo_ajeno, 'Cancha Ajena')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


def _manual(cancha, hora='14:00', fecha=MARTES, **extra):
    datos = {
        'cancha': cancha.id,
        'fecha_turno': fecha.isoformat(),
        'hora_inicio': hora,
        'nombre_cliente_manual': 'Rosendo Aquino',
        'telefono_cliente_manual': '3777 000512',
    }
    datos.update(extra)
    return datos


def _ids(respuesta):
    return [reserva['id'] for reserva in respuesta.json()['results']]


class TestConsultaDeAgenda:
    def test_el_dueno_ve_las_reservas_de_su_complejo_con_el_contacto(
        self, reloj, dueno, jugador, crear_reserva, cliente_de, complejo, cancha,
    ):
        jugador.telefono = '3777 000511'
        jugador.save()
        web = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        manual = crear_reserva(
            cancha, MARTES, time(15, 0), time(16, 0), usuario=None, creado_por=dueno,
            nombre_cliente_manual='Rosendo Aquino', telefono_cliente_manual='3777 000512',
            observaciones='Paga en efectivo',
        )

        respuesta = cliente_de(dueno).get(URL, {'complejo': complejo.id, 'fecha': MARTES.isoformat()})

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert set(cuerpo) == {'count', 'next', 'previous', 'results'}
        primera, segunda = cuerpo['results']
        assert [primera['id'], segunda['id']] == [web.id, manual.id]
        assert primera['cliente'] == {
            'nombre': 'Jugador Prueba', 'telefono': '3777 000511', 'email': 'jugador@talibre.test',
        }
        assert segunda['cliente'] == {'nombre': 'Rosendo Aquino', 'telefono': '3777 000512', 'email': None}
        assert segunda['observaciones'] == 'Paga en efectivo'
        assert segunda['complejo'] == complejo.id
        assert segunda['cancha_nombre'] == 'Cancha 1'
        assert segunda['tipo_ocupacion_nombre'] == 'Reserva manual (telefónica o presencial)'

    def test_no_expone_la_cuenta_completa_del_jugador(self, reloj, dueno, crear_reserva, cliente_de, cancha):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        (reserva,) = cliente_de(dueno).get(URL).json()['results']

        assert 'usuario' not in reserva and 'creado_por' not in reserva
        assert set(reserva['cliente']) == {'nombre', 'telefono', 'email'}

    def test_el_operador_ve_solo_su_complejo(
        self, reloj, operador, crear_reserva, cliente_de, cancha, cancha_ajena, otro_dueno,
    ):
        propia = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        crear_reserva(cancha_ajena, MARTES, time(14, 0), time(15, 0), usuario=None, creado_por=otro_dueno)

        assert _ids(cliente_de(operador).get(URL)) == [propia.id]

    def test_el_superadmin_ve_todos_los_complejos(
        self, reloj, superadmin, crear_reserva, cliente_de, cancha, cancha_ajena,
    ):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        crear_reserva(cancha_ajena, MARTES, time(14, 0), time(15, 0))

        assert cliente_de(superadmin).get(URL).json()['count'] == 2

    def test_filtrar_por_un_complejo_o_una_cancha_ajenos_responde_404(
        self, reloj, dueno, cliente_de, complejo_ajeno, cancha_ajena,
    ):
        api = cliente_de(dueno)

        assert api.get(URL, {'complejo': complejo_ajeno.id}).status_code == status.HTTP_404_NOT_FOUND
        assert api.get(URL, {'cancha': cancha_ajena.id}).status_code == status.HTTP_404_NOT_FOUND

    def test_una_reserva_ajena_responde_404(self, reloj, dueno, crear_reserva, cliente_de, cancha_ajena):
        ajena = crear_reserva(cancha_ajena, MARTES, time(14, 0), time(15, 0))

        assert cliente_de(dueno).get(_url(ajena)).status_code == status.HTTP_404_NOT_FOUND

    def test_consulta_el_detalle_de_una_reserva_propia(self, reloj, operador, crear_reserva, cliente_de, cancha):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        respuesta = cliente_de(operador).get(_url(reserva))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['id'] == reserva.id

    def test_incluye_el_historial_y_excluye_la_baja_logica(self, reloj, dueno, crear_reserva, cliente_de, cancha):
        pasada = crear_reserva(cancha, HOY - timedelta(days=7), time(14, 0), time(15, 0), estado=EstadoReserva.AUSENTE)
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.BAJA)

        assert _ids(cliente_de(dueno).get(URL)) == [pasada.id]

    def test_filtra_por_cancha_estado_tipo_y_rango(
        self, reloj, dueno, crear_reserva, cliente_de, complejo, crear_cancha, cancha,
    ):
        otra_cancha = crear_cancha(complejo, 'Cancha 2')
        web = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        manual = crear_reserva(
            otra_cancha, MARTES + timedelta(days=7), time(14, 0), time(15, 0), usuario=None,
            estado=EstadoReserva.SENADA,
        )

        api = cliente_de(dueno)

        assert _ids(api.get(URL, {'cancha': otra_cancha.id})) == [manual.id]
        assert _ids(api.get(URL, {'estado': EstadoReserva.SENADA})) == [manual.id]
        assert _ids(api.get(URL, {'tipo_ocupacion': TipoOcupacion.WEB})) == [web.id]
        assert _ids(api.get(URL, {'fecha_desde': '2026-11-20'})) == [manual.id]
        assert _ids(api.get(URL, {'fecha_hasta': '2026-11-20'})) == [web.id]

    def test_pagina_de_a_20(self, reloj, dueno, crear_reserva, cliente_de, cancha):
        for hora in range(9, 23):
            crear_reserva(cancha, MARTES, time(hora, 0), time(hora + 1, 0))
        for hora in range(14, 21):
            crear_reserva(cancha, MARTES + timedelta(days=7), time(hora, 0), time(hora + 1, 0))

        cuerpo = cliente_de(dueno).get(URL).json()

        assert cuerpo['count'] == 21 and len(cuerpo['results']) == 20

    @pytest.mark.parametrize('parametros', [
        {'fecha': '17/11/2026'}, {'estado': 0}, {'tipo_ocupacion': 9},
    ])
    def test_filtros_invalidos_responden_400(self, reloj, dueno, cliente_de, parametros):
        assert cliente_de(dueno).get(URL, parametros).status_code == status.HTTP_400_BAD_REQUEST

    def test_el_jugador_recibe_403(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN

    def test_sin_sesion_responde_401(self, cliente):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_la_cantidad_de_consultas_no_crece_con_las_reservas(
        self, reloj, dueno, crear_usuario, crear_reserva, cliente_de, cancha,
    ):
        api = cliente_de(dueno)

        def _consultas():
            with CaptureQueriesContext(connection) as capturadas:
                assert api.get(URL).status_code == status.HTTP_200_OK
            return len(capturadas)

        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        pocas = _consultas()
        for hora in range(15, 20):
            otro = crear_usuario(f'jugador{hora}@talibre.test')
            crear_reserva(cancha, MARTES, time(hora, 0), time(hora + 1, 0), usuario=otro, creado_por=otro)
        crear_reserva(cancha, MARTES, time(20, 0), time(21, 0), usuario=None)

        assert _consultas() == pocas


class TestAltaManual:
    def test_el_operador_registra_una_reserva_telefonica(self, reloj, operador, cliente_de, complejo, cancha):
        respuesta = cliente_de(operador).post(URL, _manual(cancha, observaciones='Llamó por la tarde'), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.json()
        cuerpo = respuesta.json()
        assert (cuerpo['hora_inicio'], cuerpo['hora_fin']) == ('14:00:00', '15:00:00')
        assert cuerpo['precio_acordado'] == '38000.00'
        assert cuerpo['estado'] == EstadoReserva.PENDIENTE
        assert cuerpo['tipo_ocupacion'] == TipoOcupacion.MANUAL
        assert cuerpo['cliente'] == {'nombre': 'Rosendo Aquino', 'telefono': '3777 000512', 'email': None}
        reserva = Reserva.objects.get()
        assert reserva.usuario is None and reserva.creado_por == operador
        assert reserva.observaciones == 'Llamó por la tarde'

    def test_el_telefono_y_las_observaciones_son_opcionales(self, reloj, dueno, cliente_de, cancha):
        datos = _manual(cancha)
        del datos['telefono_cliente_manual']

        respuesta = cliente_de(dueno).post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['cliente']['telefono'] == ''

    def test_sanitiza_el_nombre_y_las_observaciones(self, reloj, dueno, cliente_de, cancha):
        datos = _manual(
            cancha, nombre_cliente_manual='<script>alert(1)</script>Rosendo <b>Aquino</b>',
            observaciones='<img src=x onerror=alert(1)>Trae pelota',
        )

        cliente_de(dueno).post(URL, datos, format='json')

        reserva = Reserva.objects.get()
        assert reserva.nombre_cliente_manual == 'Rosendo Aquino'
        assert reserva.observaciones == 'Trae pelota'

    @pytest.mark.parametrize('cambios, campo', [
        ({'nombre_cliente_manual': ''}, 'nombre_cliente_manual'),
        ({'nombre_cliente_manual': '<b></b>'}, 'nombre_cliente_manual'),
        ({'telefono_cliente_manual': 'llamar a la tarde'}, 'telefono_cliente_manual'),
        ({'nombre_cliente_manual': 'x' * 121}, 'nombre_cliente_manual'),
        ({'observaciones': 'x' * 256}, 'observaciones'),
    ])
    def test_valida_los_datos_del_cliente(self, reloj, dueno, cliente_de, cancha, cambios, campo):
        respuesta = cliente_de(dueno).post(URL, _manual(cancha, **cambios), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_una_cancha_de_otro_complejo_responde_403(self, reloj, dueno, cliente_de, cancha_ajena):
        respuesta = cliente_de(dueno).post(URL, _manual(cancha_ajena), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not Reserva.objects.exists()

    def test_el_superadmin_registra_en_cualquier_complejo(self, reloj, superadmin, cliente_de, cancha_ajena):
        assert cliente_de(superadmin).post(URL, _manual(cancha_ajena), format='json').status_code == 201

    def test_el_superadmin_hereda_el_permiso_aunque_no_lo_tenga_asignado(
        self, reloj, superadmin, cliente_de, cancha,
    ):
        RolPermiso.objects.get(rol__nombre='SUPERADMIN', permiso__codigo='gestionar_agenda').desactivar()

        assert cliente_de(superadmin).post(URL, _manual(cancha), format='json').status_code == 201

    def test_el_jugador_recibe_403(self, reloj, jugador, cliente_de, cancha):
        assert cliente_de(jugador).post(URL, _manual(cancha), format='json').status_code == 403

    def test_sin_gestionar_agenda_recibe_403(self, reloj, operador, cliente_de, cancha):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='gestionar_agenda').desactivar()

        assert cliente_de(operador).post(URL, _manual(cancha), format='json').status_code == 403

    def test_choca_con_una_reserva_web_del_mismo_turno(self, reloj, dueno, crear_reserva, cliente_de, cancha):
        crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        respuesta = cliente_de(dueno).post(URL, _manual(cancha), format='json')

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert Reserva.objects.count() == 1

    def test_choca_con_un_turno_fijo(self, reloj, dueno, crear_turno_fijo, cliente_de, cancha):
        crear_turno_fijo(cancha, DiaSemana.MARTES, time(14, 0), time(15, 0), desde=HOY)

        assert cliente_de(dueno).post(URL, _manual(cancha), format='json').status_code == status.HTTP_409_CONFLICT

    def test_choca_con_una_excepcion(self, reloj, dueno, crear_excepcion_horaria, cliente_de, complejo, cancha):
        crear_excepcion_horaria(complejo, MARTES, cancha=cancha, inicio=time(13, 0), fin=time(15, 0))

        assert cliente_de(dueno).post(URL, _manual(cancha), format='json').status_code == status.HTTP_409_CONFLICT

    def test_rechaza_turnos_ya_iniciados(self, reloj, dueno, cliente_de, cancha):
        respuesta = cliente_de(dueno).post(URL, _manual(cancha, hora='09:00', fecha=HOY), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_respeta_la_anticipacion_maxima(self, reloj, dueno, cliente_de, cancha):
        respuesta = cliente_de(dueno).post(URL, _manual(cancha, fecha=date(2027, 1, 19)), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_turno' in respuesta.json()['detail']

    def test_el_limite_de_altas_no_alcanza_al_personal(self, reloj, dueno, cliente_de, cancha):
        api = cliente_de(dueno)
        for _ in range(21):
            api.post(URL, _manual(cancha, hora='14:30'), format='json')

        assert api.post(URL, _manual(cancha), format='json').status_code == status.HTTP_201_CREATED

    def test_rechaza_horarios_fuera_de_la_grilla(self, reloj, dueno, cliente_de, cancha):
        assert cliente_de(dueno).post(URL, _manual(cancha, hora='14:15'), format='json').status_code == 400

    def test_el_alta_se_audita_sin_datos_del_cliente(self, reloj, operador, cliente_de, complejo, cancha):
        cliente_de(operador).post(URL, _manual(cancha, observaciones='Cliente habitual'), format='json')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CREADA)
        assert log.usuario == operador and log.complejo == complejo
        assert 'Origen: Reserva manual' in log.detalle
        for dato in ('Rosendo', 'Aquino', '000512', 'habitual'):
            assert dato not in log.detalle

    def test_no_se_borra_por_la_api(self, reloj, dueno, crear_reserva, cliente_de, cancha):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        assert cliente_de(dueno).delete(_url(reserva)).status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Reserva.objects.filter(id=reserva.id).exists()


class TestCambioDeEstado:
    @pytest.fixture
    def reserva(self, crear_reserva, cancha):
        return crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE)

    def _patch(self, cliente_de, usuario, reserva, **datos):
        return cliente_de(usuario).patch(_url(reserva), datos, format='json')

    @pytest.mark.parametrize('anterior, nuevo', [
        (EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA),
        (EstadoReserva.PENDIENTE, EstadoReserva.SENADA),
        (EstadoReserva.CONFIRMADA, EstadoReserva.SENADA),
    ])
    def test_confirma_y_sena_antes_del_turno(self, reloj, operador, cliente_de, reserva, anterior, nuevo):
        reserva.estado = anterior
        reserva.save()

        respuesta = self._patch(cliente_de, operador, reserva, estado=nuevo)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == nuevo

    @pytest.mark.parametrize('anterior, nuevo', [
        (EstadoReserva.PENDIENTE, EstadoReserva.AUSENTE),
        (EstadoReserva.CONFIRMADA, EstadoReserva.COMPLETADA),
        (EstadoReserva.SENADA, EstadoReserva.COMPLETADA),
        (EstadoReserva.SENADA, EstadoReserva.AUSENTE),
        (EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA),
        (EstadoReserva.COMPLETADA, EstadoReserva.AUSENTE),
    ])
    def test_cierra_el_turno_una_vez_iniciado(self, reloj, operador, cliente_de, reserva, anterior, nuevo):
        reserva.estado = anterior
        reserva.save()
        reloj.return_value = reloj.return_value.replace(day=17, hour=14)

        respuesta = self._patch(cliente_de, operador, reserva, estado=nuevo)

        assert respuesta.status_code == status.HTTP_200_OK
        reserva.refresh_from_db()
        assert reserva.estado == nuevo

    @pytest.mark.parametrize('nuevo', [EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA])
    def test_no_cierra_un_turno_que_no_empezo(self, reloj, operador, cliente_de, reserva, nuevo):
        respuesta = self._patch(cliente_de, operador, reserva, estado=nuevo)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado' in respuesta.json()['detail']

    @pytest.mark.parametrize('anterior, nuevo', [
        (EstadoReserva.SENADA, EstadoReserva.CONFIRMADA),
        (EstadoReserva.CONFIRMADA, EstadoReserva.PENDIENTE),
        (EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CONFIRMADA),
        (EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.SENADA),
        (EstadoReserva.COMPLETADA, EstadoReserva.CONFIRMADA),
    ])
    def test_rechaza_transiciones_invalidas(self, reloj, operador, cliente_de, reserva, anterior, nuevo):
        reserva.estado = anterior
        reserva.save()

        respuesta = self._patch(cliente_de, operador, reserva, estado=nuevo)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        reserva.refresh_from_db()
        assert reserva.estado == anterior

    @pytest.mark.parametrize('estado', [
        EstadoReserva.BAJA, EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, 9,
    ])
    def test_cancelar_o_dar_de_baja_no_se_hace_por_patch(self, reloj, operador, cliente_de, reserva, estado):
        assert self._patch(cliente_de, operador, reserva, estado=estado).status_code == 400

    def test_edita_las_observaciones_sanitizadas(self, reloj, operador, cliente_de, reserva):
        respuesta = self._patch(cliente_de, operador, reserva, observaciones='<b>Seña</b> por transferencia')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['observaciones'] == 'Seña por transferencia'

    def test_las_observaciones_no_se_auditan(self, reloj, operador, cliente_de, reserva):
        self._patch(cliente_de, operador, reserva, observaciones='Avisó Teodoro Arrúa')

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO).exists()

    def test_el_cambio_de_estado_se_audita(self, reloj, operador, cliente_de, complejo, reserva):
        self._patch(cliente_de, operador, reserva, estado=EstadoReserva.SENADA, observaciones='Pagó Rosendo')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO)
        assert log.usuario == operador and log.complejo == complejo
        assert 'Estado: Pendiente Seña -> Señada/Pagada.' in log.detalle
        assert 'Rosendo' not in log.detalle

    def test_sin_cambios_no_audita(self, reloj, operador, cliente_de, reserva):
        respuesta = self._patch(cliente_de, operador, reserva, estado=EstadoReserva.PENDIENTE)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert self._patch(cliente_de, operador, reserva, observaciones='').status_code == status.HTTP_200_OK
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO).exists()

    def test_sin_campos_responde_400(self, reloj, operador, cliente_de, reserva):
        assert self._patch(cliente_de, operador, reserva).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize('campo, valor', [
        ('fecha_turno', '2026-11-24'), ('hora_inicio', '16:00'), ('hora_fin', '16:00'), ('precio_acordado', '1.00'),
    ])
    def test_cambiar_el_turno_o_el_precio_responde_400(self, reloj, operador, cliente_de, reserva, campo, valor):
        respuesta = self._patch(cliente_de, operador, reserva, estado=EstadoReserva.CONFIRMADA, **{campo: valor})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']
        reserva.refresh_from_db()
        assert reserva.estado == EstadoReserva.PENDIENTE

    def test_otra_cancha_responde_400(self, reloj, operador, cliente_de, complejo, crear_cancha, reserva):
        otra = crear_cancha(complejo, 'Cancha 2')

        respuesta = self._patch(cliente_de, operador, reserva, cancha=otra.id)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail']['cancha'] == ['No se edita: cancelá la reserva y registrá otra.']

    def test_reenviar_el_mismo_turno_no_es_un_error(self, reloj, operador, cliente_de, reserva, cancha):
        respuesta = self._patch(
            cliente_de, operador, reserva, estado=EstadoReserva.CONFIRMADA, cancha=cancha.id,
            fecha_turno=MARTES.isoformat(), hora_inicio='14:00', hora_fin='15:00', precio_acordado='38000.00',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoReserva.CONFIRMADA

    def test_una_reserva_ajena_responde_404(self, reloj, dueno, crear_reserva, cliente_de, cancha_ajena):
        ajena = crear_reserva(cancha_ajena, MARTES, time(14, 0), time(15, 0))

        assert self._patch(cliente_de, dueno, ajena, estado=EstadoReserva.CONFIRMADA).status_code == 404

    def test_el_jugador_no_edita_la_agenda(self, reloj, jugador, cliente_de, reserva):
        assert self._patch(cliente_de, jugador, reserva, estado=EstadoReserva.CONFIRMADA).status_code == 403

    def test_liberar_el_turno_se_anuncia(
        self, reloj, operador, cliente_de, reserva, django_capture_on_commit_callbacks,
    ):
        reloj.return_value = reloj.return_value.replace(day=17, hour=14, minute=20)
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                self._patch(cliente_de, operador, reserva, estado=EstadoReserva.CONFIRMADA)
                self._patch(cliente_de, operador, reserva, estado=EstadoReserva.AUSENTE)

        assert publicar.call_count == 1
        assert publicar.call_args.args[1]['fecha_desde'] == MARTES.isoformat()


class TestCancelacionPorElComplejo:
    @pytest.fixture
    def reserva(self, crear_reserva, cancha):
        return crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.SENADA)

    def test_cancela_sin_restriccion_horaria(self, reloj, operador, cliente_de, complejo, reserva):
        complejo.horas_limite_cancelacion = 48
        complejo.save()
        reloj.return_value = reloj.return_value.replace(day=17, hour=13, minute=50)

        respuesta = cliente_de(operador).post(_url(reserva, 'cancelar/'))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoReserva.CANCELADA_COMPLEJO
        reserva.refresh_from_db()
        assert reserva.estado == EstadoReserva.CANCELADA_COMPLEJO

    def test_cancela_aunque_el_turno_ya_haya_pasado(self, reloj, dueno, cliente_de, reserva):
        reloj.return_value = reloj.return_value.replace(day=18)

        assert cliente_de(dueno).post(_url(reserva, 'cancelar/')).status_code == status.HTTP_200_OK

    def test_el_turno_queda_libre_para_otra_reserva(self, reloj, operador, cliente_de, reserva, cancha):
        cliente_de(operador).post(_url(reserva, 'cancelar/'))

        assert cliente_de(operador).post(URL, _manual(cancha), format='json').status_code == 201

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE,
        EstadoReserva.COMPLETADA,
    ])
    def test_una_reserva_cerrada_no_se_cancela(self, reloj, operador, cliente_de, reserva, estado):
        reserva.estado = estado
        reserva.save()

        assert cliente_de(operador).post(_url(reserva, 'cancelar/')).status_code == status.HTTP_400_BAD_REQUEST

    def test_una_reserva_ajena_responde_404(self, reloj, dueno, crear_reserva, cliente_de, cancha_ajena):
        ajena = crear_reserva(cancha_ajena, MARTES, time(14, 0), time(15, 0))

        assert cliente_de(dueno).post(_url(ajena, 'cancelar/')).status_code == status.HTTP_404_NOT_FOUND
        ajena.refresh_from_db()
        assert ajena.estado == EstadoReserva.CONFIRMADA

    def test_el_superadmin_cancela_en_cualquier_complejo(self, reloj, superadmin, crear_reserva, cliente_de, cancha_ajena):
        ajena = crear_reserva(cancha_ajena, MARTES, time(14, 0), time(15, 0))

        assert cliente_de(superadmin).post(_url(ajena, 'cancelar/')).status_code == status.HTTP_200_OK

    def test_el_jugador_no_cancela_como_complejo(self, reloj, jugador, cliente_de, reserva):
        assert cliente_de(jugador).post(_url(reserva, 'cancelar/')).status_code == status.HTTP_403_FORBIDDEN

    def test_sin_el_permiso_de_cancelar_recibe_403(self, reloj, operador, cliente_de, reserva):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='cancelar_reserva_complejo').desactivar()

        assert cliente_de(operador).post(_url(reserva, 'cancelar/')).status_code == status.HTTP_403_FORBIDDEN

    def test_se_audita_y_se_anuncia(
        self, reloj, operador, cliente_de, complejo, reserva, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                cliente_de(operador).post(_url(reserva, 'cancelar/'))

        publicar.assert_called_once()
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_CANCELADA)
        assert log.usuario == operador and log.complejo == complejo
        assert 'Señada/Pagada -> Cancelada por el complejo.' in log.detalle


class TestReservaQueDesaparecioAlBloquear:
    """Entre la lectura de la vista y el bloqueo, otra operación pudo dar de baja la reserva."""

    @pytest.fixture
    def dada_de_baja(self, crear_reserva, cancha):
        return crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.BAJA)

    def test_el_cambio_de_estado_responde_404(self, reloj, operador, dada_de_baja):
        with pytest.raises(NotFound):
            ReservaService.actualizar_en_agenda(dada_de_baja.id, {'estado': EstadoReserva.CONFIRMADA}, operador, None)

    def test_la_cancelacion_del_complejo_responde_404(self, reloj, operador, dada_de_baja):
        with pytest.raises(NotFound):
            ReservaService.cancelar_por_complejo(dada_de_baja.id, operador, None)

    def test_la_cancelacion_del_jugador_exige_que_sea_suya(self, reloj, crear_usuario, crear_reserva, cancha):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))
        otro = crear_usuario('otro.jugador@talibre.test')

        with pytest.raises(NotFound):
            ReservaService.cancelar_por_jugador(reserva.id, otro, None)
