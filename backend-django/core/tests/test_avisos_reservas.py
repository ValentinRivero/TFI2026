from datetime import time, timedelta
from unittest import mock

import pytest
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import DiaSemana, EstadoReserva, EstadoUsuario, Reserva, TipoOcupacion
from core.services import (
    CATEGORIA_AVISO_RESERVAS,
    PRIORIDAD_AVISO_NORMAL,
    PRIORIDAD_AVISO_URGENTE,
    TIPO_EVENTO_RESERVA_REALIZADA,
    AvisoComplejoService,
)
from core.tests.test_avisos_node import CLAVE, NodeSimulado

MARTES = HOY_CONGELADO + timedelta(days=1)


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def avisos(django_capture_on_commit_callbacks):
    """Ejecuta los callbacks de commit del bloque y junta los avisos que se habrían entregado a backend-node."""
    entregados = []

    class Captura:
        def __enter__(self):
            self.parche = mock.patch.object(AvisoComplejoService, 'entregar', side_effect=entregados.append)
            self.parche.start()
            self.commit = django_capture_on_commit_callbacks(execute=True)
            self.commit.__enter__()
            return entregados

        def __exit__(self, *args):
            self.commit.__exit__(*args)
            self.parche.stop()

    return Captura()


def _reservar(cliente_de, usuario, cancha, hora='14:00'):
    datos = {'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': hora}
    return cliente_de(usuario).post('/api/reservas/', datos, format='json')


def _manual(cliente_de, usuario, cancha, hora='15:00'):
    datos = {
        'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': hora,
        'nombre_cliente_manual': 'Rosendo Aquino', 'telefono_cliente_manual': '3777 000512',
    }
    return cliente_de(usuario).post('/api/agenda/', datos, format='json')


def _cancelar_desde_agenda(cliente_de, usuario, reserva_id):
    return cliente_de(usuario).post(f'/api/agenda/{reserva_id}/cancelar/')


class TestReservaRealizada:
    def test_una_reserva_web_registra_el_evento_y_avisa_al_personal_y_al_jugador(
        self, reloj, jugador, dueno, complejo, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            respuesta = _reservar(cliente_de, jugador, cancha)

        assert respuesta.status_code == status.HTTP_201_CREATED
        reserva_id = respuesta.json()['id']
        aviso, constancia = entregados
        assert aviso['complejo_id'] == complejo.id and aviso['usuario_id'] is None
        assert aviso['usuarios_ids'] == [dueno.id]
        assert (aviso['categoria'], aviso['prioridad']) == (CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL)
        assert constancia['usuario_id'] == jugador.id and constancia['evento'] is None
        assert aviso['evento'] == {
            'tipo_evento': TIPO_EVENTO_RESERVA_REALIZADA,
            'usuario_id': jugador.id,
            'metadata': {
                'reserva_id': reserva_id, 'cancha_id': cancha.id,
                'fecha_turno': MARTES.isoformat(), 'hora_inicio': '14:00',
            },
        }
        assert aviso['mensaje'] == (
            f'{complejo.nombre}: nueva reserva web id {reserva_id}: Cancha 1, el {MARTES:%d/%m/%Y} de 14:00 a 15:00. '
            'Pendiente de seña.'
        )

    def test_el_aviso_no_tiene_datos_personales_del_jugador(self, reloj, jugador, cancha, cliente_de, avisos):
        with avisos as entregados:
            _reservar(cliente_de, jugador, cancha)

        for aviso in entregados:
            for dato in (jugador.nombre_completo, jugador.email, jugador.telefono):
                if dato:
                    assert dato not in aviso['mensaje']

    def test_una_reserva_por_graphql_avisa_igual_que_por_rest(self, reloj, jugador, cancha, cliente_de, avisos):
        mutacion = '''mutation($c: Int!, $f: String!, $h: String!) {
          crearReserva(cancha: $c, fechaTurno: $f, horaInicio: $h) { reserva { id } } }'''

        with avisos as entregados:
            respuesta = cliente_de(jugador).post(
                '/graphql/', {'query': mutacion, 'variables': {'c': cancha.id, 'f': MARTES.isoformat(), 'h': '16:00'}},
                format='json',
            )

        assert respuesta.json()['data']['crearReserva']['reserva']['id']
        assert [aviso['evento']['tipo_evento'] for aviso in entregados if aviso['evento']] == [
            TIPO_EVENTO_RESERVA_REALIZADA,
        ]

    def test_una_reserva_manual_no_avisa_a_quien_la_cargo_sino_al_resto_del_personal(
        self, reloj, dueno, operador, complejo, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            respuesta = _manual(cliente_de, operador, cancha)

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['tipo_ocupacion'] == TipoOcupacion.MANUAL
        (aviso,) = entregados
        assert aviso['usuarios_ids'] == [dueno.id] and aviso['complejo_id'] == complejo.id
        assert aviso['evento'] is None and 'reserva manual' in aviso['mensaje']

    def test_una_reserva_manual_cargada_por_el_unico_personal_no_avisa_a_nadie(
        self, reloj, dueno, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            _manual(cliente_de, dueno, cancha)

        (registro,) = entregados
        assert registro['usuarios_ids'] is None and registro['registro']['ambito'] == 1

    def test_una_reserva_rechazada_no_avisa(self, reloj, jugador, crear_usuario, cancha, cliente_de, avisos):
        _reservar(cliente_de, jugador, cancha)
        otro = crear_usuario('otro.jugador@test.com')

        with avisos as entregados:
            respuesta = _reservar(cliente_de, otro, cancha)

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert entregados == []

    def test_con_node_caido_la_reserva_se_confirma_igual(
        self, reloj, settings, jugador, cancha, cliente_de, django_capture_on_commit_callbacks,
    ):
        with NodeSimulado() as apagado:
            url = apagado.url
        settings.NODE_API_URL, settings.INTERNAL_API_KEY = url, CLAVE

        with django_capture_on_commit_callbacks(execute=True):
            respuesta = _reservar(cliente_de, jugador, cancha)

        assert respuesta.status_code == status.HTTP_201_CREATED


class TestCancelacionPorElComplejo:
    @pytest.fixture
    def reserva_web(self, reloj, jugador, cancha, cliente_de):
        return _reservar(cliente_de, jugador, cancha).json()['id']

    def test_avisa_al_jugador_en_su_bandeja_propia(
        self, jugador, operador, complejo, reserva_web, cliente_de, avisos,
    ):
        with avisos as entregados:
            respuesta = _cancelar_desde_agenda(cliente_de, operador, reserva_web)

        assert respuesta.status_code == status.HTTP_200_OK
        aviso = next(aviso for aviso in entregados if aviso['usuario_id'] == jugador.id)
        assert aviso['complejo_id'] is None
        assert (aviso['categoria'], aviso['prioridad']) == (CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_URGENTE)
        assert aviso['evento'] is None
        assert aviso['mensaje'] == (
            f'{complejo.nombre} canceló tu reserva id {reserva_web} (Cancha 1, el {MARTES:%d/%m/%Y} de 14:00 a '
            '15:00). Si habías pagado una seña, comunicate con el complejo.'
        )

    def test_el_aviso_no_identifica_a_quien_cancelo(self, operador, reserva_web, cliente_de, avisos):
        with avisos as entregados:
            _cancelar_desde_agenda(cliente_de, operador, reserva_web)

        for aviso in entregados:
            assert operador.nombre_completo not in aviso['mensaje']
            assert operador.email not in aviso['mensaje']

    def test_una_reserva_manual_no_tiene_a_quien_avisar(self, reloj, dueno, cancha, cliente_de, avisos):
        reserva_id = _manual(cliente_de, dueno, cancha).json()['id']

        with avisos as entregados:
            respuesta = _cancelar_desde_agenda(cliente_de, dueno, reserva_id)

        assert respuesta.status_code == status.HTTP_200_OK
        assert [aviso['usuario_id'] for aviso in entregados] == [None]

    def test_no_avisa_a_un_titular_que_dio_de_baja_su_cuenta(self, jugador, dueno, reserva_web, cliente_de, avisos):
        jugador.estado = EstadoUsuario.BAJA
        jugador.save(update_fields=['estado'])

        with avisos as entregados:
            _cancelar_desde_agenda(cliente_de, dueno, reserva_web)

        assert [aviso['usuario_id'] for aviso in entregados] == [None]

    def test_una_cancelacion_rechazada_no_avisa(self, dueno, reserva_web, cliente_de, avisos):
        _cancelar_desde_agenda(cliente_de, dueno, reserva_web)

        with avisos as entregados:
            respuesta = _cancelar_desde_agenda(cliente_de, dueno, reserva_web)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert entregados == []

    def test_la_cancelacion_del_propio_jugador_le_llega_como_constancia_y_avisa_al_personal(
        self, jugador, dueno, reserva_web, cliente_de, avisos,
    ):
        with avisos as entregados:
            respuesta = cliente_de(jugador).post(f'/api/reservas/{reserva_web}/cancelar/')

        assert respuesta.status_code == status.HTTP_200_OK
        constancia = next(aviso for aviso in entregados if aviso['usuario_id'] == jugador.id)
        personal = next(aviso for aviso in entregados if aviso['usuarios_ids'] == [dueno.id])
        assert 'Procesamos la cancelación' in constancia['mensaje']
        assert 'el titular canceló' in personal['mensaje']


class TestDeExtremoAExtremo:
    def test_reservar_y_cancelar_llegan_a_backend_node(
        self, reloj, settings, jugador, dueno, operador, complejo, cancha, cliente_de,
        django_capture_on_commit_callbacks,
    ):
        with NodeSimulado() as node:
            settings.NODE_API_URL, settings.INTERNAL_API_KEY = node.url, CLAVE
            with django_capture_on_commit_callbacks(execute=True):
                reserva_id = _reservar(cliente_de, jugador, cancha).json()['id']
            with django_capture_on_commit_callbacks(execute=True):
                _cancelar_desde_agenda(cliente_de, operador, reserva_id)

        alta, constancia, cancelacion, aviso_al_personal = (pedido['cuerpo'] for pedido in node.pedidos)
        assert aviso_al_personal['usuarios_ids'] == [dueno.id]
        assert alta['complejo_id'] == complejo.id and alta['usuarios_ids'] == [dueno.id, operador.id]
        assert alta['evento']['tipo_evento'] == TIPO_EVENTO_RESERVA_REALIZADA
        assert alta['evento']['metadata']['reserva_id'] == reserva_id
        assert constancia['usuario_id'] == jugador.id
        assert cancelacion['usuario_id'] == jugador.id and 'complejo_id' not in cancelacion
        assert cancelacion['prioridad'] == PRIORIDAD_AVISO_URGENTE
        assert Reserva.objects.get(pk=reserva_id).estado == EstadoReserva.CANCELADA_COMPLEJO
