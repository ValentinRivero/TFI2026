from datetime import time, timedelta

import pytest
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import DiaSemana, EstadoReserva, LogAuditoria, TipoEventoAuditoria

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)
URL_AGENDA = '/api/agenda/'

ESTADOS_EDITABLES = [
    EstadoReserva.PENDIENTE,
    EstadoReserva.CONFIRMADA,
    EstadoReserva.SENADA,
    EstadoReserva.CANCELADA_JUGADOR,
    EstadoReserva.CANCELADA_COMPLEJO,
    EstadoReserva.AUSENTE,
    EstadoReserva.COMPLETADA,
]


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def reserva(cancha, crear_reserva):
    return crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), observaciones='Trae pelota')


def _editar(api, reserva, texto):
    return api.patch(f'{URL_AGENDA}{reserva.id}/', {'observaciones': texto}, format='json')


class TestEdicionDeObservaciones:
    @pytest.mark.parametrize('estado', ESTADOS_EDITABLES)
    def test_se_editan_en_cualquier_estado_sin_cambiar_el_resto(self, reloj, dueno, cliente_de, reserva, estado):
        reserva.estado = estado
        reserva.save()

        respuesta = _editar(cliente_de(dueno), reserva, 'Pidió factura')

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        reserva.refresh_from_db()
        assert reserva.observaciones == 'Pidió factura'
        assert reserva.estado == estado

    def test_el_operador_tambien_las_edita(self, reloj, operador, cliente_de, reserva):
        assert _editar(cliente_de(operador), reserva, 'Llega tarde').status_code == status.HTTP_200_OK

    def test_el_superadmin_las_edita_en_cualquier_complejo(self, reloj, superadmin, cliente_de, reserva):
        assert _editar(cliente_de(superadmin), reserva, 'Soporte').status_code == status.HTTP_200_OK

    def test_se_pueden_vaciar(self, reloj, dueno, cliente_de, reserva):
        respuesta = _editar(cliente_de(dueno), reserva, '')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['observaciones'] == ''

    def test_limpia_el_html_y_recorta_los_espacios(self, reloj, dueno, cliente_de, reserva):
        respuesta = _editar(cliente_de(dueno), reserva, '  <script>alert(1)</script><b>Cancha</b> con luz  ')

        assert respuesta.json()['observaciones'] == 'Cancha con luz'

    def test_se_guardan_como_texto_aunque_traigan_marcas(self, reloj, dueno, cliente_de, reserva):
        respuesta = _editar(cliente_de(dueno), reserva, 'Cobrar 5 < 10 & más')

        assert respuesta.status_code == status.HTTP_200_OK
        reserva.refresh_from_db()
        assert reserva.observaciones == 'Cobrar 5 < 10 & más'

    def test_el_limite_es_de_255_caracteres(self, reloj, dueno, cliente_de, reserva):
        api = cliente_de(dueno)

        assert _editar(api, reserva, 'x' * 255).status_code == status.HTTP_200_OK
        rechazada = _editar(api, reserva, 'x' * 256)

        assert rechazada.status_code == status.HTTP_400_BAD_REQUEST
        reserva.refresh_from_db()
        assert reserva.observaciones == 'x' * 255

    def test_un_valor_que_no_es_texto_responde_400(self, reloj, dueno, cliente_de, reserva):
        assert _editar(cliente_de(dueno), reserva, {'a': 1}).status_code == status.HTTP_400_BAD_REQUEST

    def test_actualiza_la_fecha_de_modificacion_solo_si_hay_cambio(self, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        antes = reserva.fecha_modificacion

        assert _editar(api, reserva, 'Trae pelota').status_code == status.HTTP_200_OK
        reserva.refresh_from_db()
        assert reserva.fecha_modificacion == antes

        _editar(api, reserva, 'Otra nota')
        reserva.refresh_from_db()
        assert reserva.fecha_modificacion > antes

    def test_no_se_audita_el_contenido(self, reloj, dueno, cliente_de, reserva):
        _editar(cliente_de(dueno), reserva, 'Avisó Teodoro Arrúa')

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.RESERVA_CAMBIO_ESTADO).exists()
        assert not LogAuditoria.objects.filter(detalle__contains='Teodoro').exists()

    def test_el_jugador_titular_no_las_ve_ni_las_edita(self, reloj, jugador, cliente_de, reserva):
        api = cliente_de(jugador)

        assert _editar(api, reserva, 'Nota propia').status_code == status.HTTP_403_FORBIDDEN
        propias = api.get('/api/reservas/mias/').json()['results']
        assert all('observaciones' not in fila for fila in propias)

    def test_sin_sesion_responde_401(self, cliente, reserva):
        assert _editar(cliente, reserva, 'Nota').status_code == status.HTTP_401_UNAUTHORIZED

    def test_un_dueno_ajeno_responde_404_y_no_modifica(self, reloj, otro_dueno, cliente_de, reserva):
        assert _editar(cliente_de(otro_dueno), reserva, 'Intruso').status_code == status.HTTP_404_NOT_FOUND
        reserva.refresh_from_db()
        assert reserva.observaciones == 'Trae pelota'

    def test_una_reserva_dada_de_baja_responde_404(self, reloj, dueno, cliente_de, reserva):
        reserva.estado = EstadoReserva.BAJA
        reserva.save()

        assert _editar(cliente_de(dueno), reserva, 'Nota').status_code == status.HTTP_404_NOT_FOUND

    def test_editar_observaciones_junto_con_un_turno_distinto_sigue_rechazado(self, reloj, dueno, cliente_de, reserva):
        respuesta = cliente_de(dueno).patch(
            f'{URL_AGENDA}{reserva.id}/', {'observaciones': 'Nota', 'hora_inicio': '16:00'}, format='json',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        reserva.refresh_from_db()
        assert reserva.observaciones == 'Trae pelota'
