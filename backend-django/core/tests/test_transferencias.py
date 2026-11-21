from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import (
    DiaSemana,
    EstadoPago,
    EstadoReserva,
    EstadoUsuario,
    LogAuditoria,
    Reserva,
    TipoEventoAuditoria,
)
from core.repositories import ReservaRepository
from core.services import AMBITO_REGISTRO_OPERATIVO
from core.tests.test_avisos_reservas import avisos  # noqa: F401

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)
URL_AGENDA = '/api/agenda/'
URL_MIAS = '/api/reservas/mias/'
TITULAR = 'Marta López'
REFERENCIA = 'OP-48213'


def _url(reserva):
    return f'/api/reservas/{reserva.id}/informar-transferencia/'


def _informar(api, reserva, titular=TITULAR, referencia=REFERENCIA):
    return api.post(_url(reserva), {'titular': titular, 'referencia': referencia}, format='json')


@pytest.fixture
def con_sena(complejo):
    complejo.porcentaje_sena = 30
    complejo.alias_transferencia = 'YACARE.TEST.SENA'
    complejo.save()
    return complejo


@pytest.fixture
def cancha(con_sena, crear_cancha, crear_horario):
    cancha = crear_cancha(con_sena, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def reserva(cancha, crear_reserva):
    """Reserva del jugador con la seña pendiente de transferir."""
    return crear_reserva(
        cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE,
        precio_acordado=Decimal('38000.00'), monto_sena=Decimal('11400.00'),
    )


class TestInformarTransferencia:
    def test_el_titular_informa_la_transferencia(self, reloj, jugador, cliente_de, reserva):
        antes = reserva.estado

        respuesta = _informar(cliente_de(jugador), reserva)

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['transferencia_informada'] is True
        assert cuerpo['transferencia']['titular'] == TITULAR
        assert cuerpo['transferencia']['referencia'] == REFERENCIA
        assert cuerpo['transferencia']['informada_en']
        reserva.refresh_from_db()
        assert (reserva.estado, reserva.monto_pagado) == (antes, Decimal('0'))
        assert reserva.estado_pago == EstadoPago.SENA_PENDIENTE

    def test_antes_de_informar_no_hay_datos(self, reloj, jugador, cliente_de, reserva):
        (fila,) = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert fila['transferencia_informada'] is False and fila['transferencia'] is None

    def test_funciona_con_la_reserva_confirmada(self, reloj, jugador, cliente_de, reserva):
        reserva.estado = EstadoReserva.CONFIRMADA
        reserva.save()

        assert _informar(cliente_de(jugador), reserva).status_code == status.HTTP_200_OK

    def test_limpia_el_html_y_colapsa_los_espacios(self, reloj, jugador, cliente_de, reserva):
        respuesta = _informar(
            cliente_de(jugador), reserva, titular='  <b>María</b>   José   Pérez ', referencia=' <i>OP-1234</i> ',
        )

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        reserva.refresh_from_db()
        assert (reserva.transferencia_titular, reserva.transferencia_referencia) == ('María José Pérez', 'OP-1234')

    def test_acepta_una_razon_social(self, reloj, jugador, cliente_de, reserva):
        assert _informar(cliente_de(jugador), reserva, titular='Pérez & Hijos S.A.').status_code == status.HTTP_200_OK

    def test_corregir_mientras_la_sena_sigue_pendiente(self, jugador, cliente_de, reserva):
        api = cliente_de(jugador)
        _informar(api, reserva)
        primera = Reserva.objects.get(pk=reserva.pk).transferencia_informada_en

        respuesta = _informar(api, reserva, referencia='OP-48214')

        assert respuesta.status_code == status.HTTP_200_OK
        reserva.refresh_from_db()
        assert reserva.transferencia_referencia == 'OP-48214'
        assert reserva.transferencia_informada_en > primera

    def test_repetir_los_mismos_datos_es_idempotente(self, jugador, cliente_de, reserva, avisos):
        api = cliente_de(jugador)
        _informar(api, reserva)
        informada = Reserva.objects.get(pk=reserva.pk).transferencia_informada_en

        with avisos as entregados:
            respuesta = _informar(api, reserva)

        assert respuesta.status_code == status.HTTP_200_OK
        assert entregados == []
        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA).count() == 1
        reserva.refresh_from_db()
        assert reserva.transferencia_informada_en == informada

    def test_repetir_los_datos_con_otros_espacios_tambien_es_idempotente(self, jugador, cliente_de, reserva):
        api = cliente_de(jugador)
        _informar(api, reserva, titular='Marta López')
        _informar(api, reserva, titular='  Marta   López ')

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA).count() == 1


class TestRechazos:
    @pytest.mark.parametrize('estado, texto', [
        (EstadoReserva.SENADA, 'ya está registrada'),
        (EstadoReserva.CANCELADA_JUGADOR, 'no admite informar'),
        (EstadoReserva.CANCELADA_COMPLEJO, 'no admite informar'),
        (EstadoReserva.AUSENTE, 'no admite informar'),
        (EstadoReserva.COMPLETADA, 'no admite informar'),
    ])
    def test_estados_que_no_admiten_el_aviso(self, reloj, jugador, cliente_de, reserva, estado, texto):
        reserva.estado = estado
        reserva.save()

        respuesta = _informar(cliente_de(jugador), reserva)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert texto in respuesta.json()['detail']
        reserva.refresh_from_db()
        assert not reserva.transferencia_informada

    def test_una_reserva_sin_sena_no_se_informa(self, reloj, jugador, cliente_de, cancha, crear_reserva):
        sin_sena = crear_reserva(cancha, MARTES, time(15, 0), time(16, 0), estado=EstadoReserva.PENDIENTE)

        respuesta = _informar(cliente_de(jugador), sin_sena)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail'] == 'Esta reserva no exige seña.'

    def test_una_reserva_con_la_sena_abonada_no_se_informa(self, reloj, jugador, cliente_de, reserva):
        reserva.monto_pagado = reserva.monto_sena
        reserva.save()

        assert _informar(cliente_de(jugador), reserva).status_code == status.HTTP_400_BAD_REQUEST

    def test_una_reserva_saldada_no_se_informa(self, reloj, jugador, cliente_de, reserva):
        reserva.monto_pagado = reserva.precio_acordado
        reserva.save()

        assert _informar(cliente_de(jugador), reserva).status_code == status.HTTP_400_BAD_REQUEST

    def test_no_se_puede_corregir_despues_de_confirmada_la_sena(self, reloj, jugador, dueno, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva)
        cliente_de(dueno).post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        respuesta = _informar(cliente_de(jugador), reserva, referencia='OP-99999')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        reserva.refresh_from_db()
        assert reserva.transferencia_referencia == REFERENCIA

    @pytest.mark.parametrize('titular', [
        '', '   ', 'A', '12', 'x' * 101, '<b></b>', '<script>alert(1)</script>', 'Marta; DROP TABLE', None,
    ])
    def test_titular_invalido(self, reloj, jugador, cliente_de, reserva, titular):
        respuesta = _informar(cliente_de(jugador), reserva, titular=titular)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'titular' in respuesta.json()['detail']

    def test_los_caracteres_de_control_se_descartan(self, reloj, jugador, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva, titular='Marta\u0000 López')

        reserva.refresh_from_db()
        assert '\u0000' not in reserva.transferencia_titular

    @pytest.mark.parametrize('referencia', [
        '', '  ', 'ab', 'x' * 61, 'con espacio', '../etc/passwd', '<script>alert(1)</script>', '-OP123', 'OP;123', 'OP\n123', None,
    ])
    def test_referencia_invalida(self, reloj, jugador, cliente_de, reserva, referencia):
        respuesta = _informar(cliente_de(jugador), reserva, referencia=referencia)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'referencia' in respuesta.json()['detail']

    @pytest.mark.parametrize('referencia', ['ABC', 'OP-48213', '0012345678', 'A1.B2_C3/D4-E5', 'x' * 60])
    def test_referencias_validas(self, reloj, jugador, cliente_de, reserva, referencia):
        assert _informar(cliente_de(jugador), reserva, referencia=referencia).status_code == status.HTTP_200_OK

    def test_faltan_los_dos_campos(self, reloj, jugador, cliente_de, reserva):
        respuesta = cliente_de(jugador).post(_url(reserva), {}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert {'titular', 'referencia'} <= set(respuesta.json()['detail'])

    def test_un_rechazo_no_modifica_lo_ya_informado(self, reloj, jugador, cliente_de, reserva):
        api = cliente_de(jugador)
        _informar(api, reserva)

        _informar(api, reserva, referencia='no valida')

        reserva.refresh_from_db()
        assert reserva.transferencia_referencia == REFERENCIA

    def test_limite_de_avisos_por_cuenta(self, jugador, cliente_de, reserva):
        api = cliente_de(jugador)

        codigos = [_informar(api, reserva, referencia=f'OP-{numero:05d}').status_code for numero in range(11)]

        assert codigos[:10] == [status.HTTP_200_OK] * 10
        assert codigos[10] == status.HTTP_429_TOO_MANY_REQUESTS


class TestAislamiento:
    def test_sin_sesion_responde_401(self, cliente, reserva):
        assert _informar(cliente, reserva).status_code == status.HTTP_401_UNAUTHORIZED

    def test_otro_jugador_responde_404_y_no_modifica(self, reloj, crear_usuario, cliente_de, reserva):
        otro = crear_usuario('otra.jugadora@talibre.test')

        assert _informar(cliente_de(otro), reserva).status_code == status.HTTP_404_NOT_FOUND
        reserva.refresh_from_db()
        assert not reserva.transferencia_informada

    @pytest.mark.parametrize('rol', ['dueno', 'operador', 'otro_dueno', 'superadmin'])
    def test_el_personal_no_informa_por_el_jugador(self, reloj, request, cliente_de, reserva, rol):
        usuario = request.getfixturevalue(rol)

        respuesta = _informar(cliente_de(usuario), reserva)

        assert respuesta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        reserva.refresh_from_db()
        assert not reserva.transferencia_informada

    def test_una_reserva_manual_o_inexistente_responde_404(self, reloj, jugador, cliente_de):
        assert cliente_de(jugador).post('/api/reservas/99999/informar-transferencia/', {}, format='json').status_code == 404


class TestVisibilidad:
    def test_el_personal_del_complejo_ve_lo_informado_en_la_agenda(self, reloj, jugador, operador, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva)

        fila = cliente_de(operador).get(f'{URL_AGENDA}{reserva.id}/').json()

        assert fila['transferencia_informada'] is True
        assert (fila['transferencia']['titular'], fila['transferencia']['referencia']) == (TITULAR, REFERENCIA)

    def test_la_lista_de_la_agenda_marca_las_transferencias_informadas(self, reloj, jugador, dueno, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva)

        (fila,) = cliente_de(dueno).get(URL_AGENDA).json()['results']

        assert fila['transferencia_informada'] is True

    def test_otro_complejo_no_ve_la_reserva_ni_la_transferencia(self, reloj, jugador, otro_dueno, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva)

        assert cliente_de(otro_dueno).get(f'{URL_AGENDA}{reserva.id}/').status_code == status.HTTP_404_NOT_FOUND
        assert TITULAR not in str(cliente_de(otro_dueno).get(URL_AGENDA).json())

    def test_otro_jugador_no_la_ve_en_sus_reservas(self, reloj, jugador, crear_usuario, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva)
        otro = crear_usuario('otra.jugadora@talibre.test')

        assert cliente_de(otro).get(URL_MIAS).json()['results'] == []

    def test_los_datos_no_salen_en_ninguna_ruta_publica(self, reloj, jugador, cliente, cliente_de, reserva, cancha, con_sena):
        _informar(cliente_de(jugador), reserva)

        publico = ''.join(
            str(cliente.get(ruta).json()) for ruta in (
                '/api/complejos/', f'/api/complejos/{con_sena.id}/',
                f'/api/complejos/{con_sena.id}/grilla/?fecha={MARTES.isoformat()}',
            )
        )

        assert TITULAR not in publico and REFERENCIA not in publico

    def test_graphql_expone_lo_mismo_que_rest_solo_al_titular(self, reloj, jugador, cliente_de, reserva):
        api = cliente_de(jugador)
        _informar(api, reserva)
        consulta = '''{ misReservas { results { transferenciaInformada
          transferencia { titular referencia informadaEn } } } }'''

        graphql = api.post('/graphql/', {'query': consulta}, format='json').json()['data']['misReservas']['results'][0]
        rest = api.get(URL_MIAS).json()['results'][0]

        assert graphql['transferenciaInformada'] is True
        assert graphql['transferencia'] == {
            'titular': rest['transferencia']['titular'], 'referencia': rest['transferencia']['referencia'],
            'informadaEn': rest['transferencia']['informada_en'],
        }


class TestConciliacionDelPersonal:
    @pytest.mark.parametrize('informar', [True, False])
    def test_confirmar_la_sena_funciona_con_o_sin_aviso_previo(self, reloj, jugador, dueno, cliente_de, reserva, informar):
        if informar:
            _informar(cliente_de(jugador), reserva)

        respuesta = cliente_de(dueno).post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado_pago'] == EstadoPago.SENA_ABONADA
        assert respuesta.json()['transferencia_informada'] is informar

    @pytest.mark.parametrize('informar', [True, False])
    def test_registrar_el_pago_funciona_con_o_sin_aviso_previo(self, reloj, jugador, operador, cliente_de, reserva, informar):
        if informar:
            _informar(cliente_de(jugador), reserva)

        respuesta = cliente_de(operador).post(f'{URL_AGENDA}{reserva.id}/registrar-pago/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado_pago'] == EstadoPago.PAGADA

    def test_el_jugador_sigue_viendo_lo_informado_con_la_sena_confirmada(self, reloj, jugador, dueno, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva)
        cliente_de(dueno).post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        (fila,) = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert fila['transferencia']['referencia'] == REFERENCIA
        assert fila['datos_transferencia'] is None


class TestAuditoriaYAvisos:
    def test_audita_sin_datos_personales(self, reloj, jugador, cliente_de, reserva, con_sena):
        _informar(cliente_de(jugador), reserva)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA)
        assert log.accion == 'Transferencia de seña informada'
        assert (log.usuario_id, log.complejo_id) == (jugador.id, con_sena.id)
        assert f'Reserva id {reserva.id}' in log.detalle
        for dato in (TITULAR, 'Marta', 'López', REFERENCIA, '48213', jugador.email):
            assert dato not in log.detalle and dato not in log.accion

    def test_distingue_el_aviso_inicial_de_la_correccion(self, reloj, jugador, cliente_de, reserva):
        api = cliente_de(jugador)
        _informar(api, reserva)
        _informar(api, reserva, referencia='OP-48214')

        acciones = list(
            LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA)
            .order_by('id').values_list('accion', flat=True)
        )

        assert acciones == ['Transferencia de seña informada', 'Corrección de transferencia de seña']

    def test_la_auditoria_de_la_correccion_tampoco_guarda_datos(self, reloj, jugador, cliente_de, reserva):
        api = cliente_de(jugador)
        _informar(api, reserva)
        _informar(api, reserva, titular='Roberto Gómez', referencia='OP-777')

        for log in LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA):
            assert 'Roberto' not in log.detalle and '777' not in log.detalle

    def test_un_rechazo_no_audita(self, reloj, jugador, cliente_de, reserva):
        _informar(cliente_de(jugador), reserva, referencia='no valida')

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA).exists()

    def test_avisa_al_dueno_y_a_los_operadores_del_complejo(
        self, reloj, jugador, dueno, operador, cliente_de, reserva, con_sena, avisos,
    ):
        with avisos as entregados:
            _informar(cliente_de(jugador), reserva)

        (aviso,) = entregados
        assert aviso['complejo_id'] == con_sena.id
        assert sorted(aviso['usuarios_ids']) == sorted([dueno.id, operador.id])
        assert f'informó la transferencia de la seña de la reserva id {reserva.id}' in aviso['mensaje']
        assert 'Cancha 1' in aviso['mensaje'] and f'{MARTES:%d/%m/%Y}' in aviso['mensaje'] and '14:00' in aviso['mensaje']

    def test_el_aviso_no_lleva_datos_personales(self, reloj, jugador, cliente_de, reserva, avisos):
        with avisos as entregados:
            _informar(cliente_de(jugador), reserva)

        for aviso in entregados:
            texto = f"{aviso['mensaje']} {aviso['registro']['mensaje']}"
            for dato in (TITULAR, 'Marta', 'López', REFERENCIA, '48213', jugador.nombre_completo, jugador.email):
                assert dato not in texto

    def test_queda_en_el_registro_del_complejo(self, reloj, jugador, cliente_de, reserva, avisos):
        with avisos as entregados:
            _informar(cliente_de(jugador), reserva)

        (aviso,) = entregados
        assert aviso['registro']['ambito'] == AMBITO_REGISTRO_OPERATIVO
        assert f'Titular y autor: usuario id {jugador.id}' in aviso['registro']['mensaje']
        assert 'Hecho por' not in aviso['registro']['mensaje']

    def test_la_correccion_avisa_como_correccion(self, reloj, jugador, cliente_de, reserva, avisos):
        api = cliente_de(jugador)
        _informar(api, reserva)

        with avisos as entregados:
            _informar(api, reserva, referencia='OP-48214')

        (aviso,) = entregados
        assert 'corrigió los datos de la transferencia' in aviso['mensaje']

    def test_un_operador_suspendido_no_recibe_el_aviso(self, reloj, jugador, dueno, operador, cliente_de, reserva, avisos):
        operador.estado = EstadoUsuario.SUSPENDIDO
        operador.save()

        with avisos as entregados:
            _informar(cliente_de(jugador), reserva)

        assert entregados[0]['usuarios_ids'] == [dueno.id]


class TestRetencion:
    def test_el_nombre_de_quien_transfirio_se_borra_con_el_de_la_baja(self, jugador, cancha, crear_reserva):
        reserva = crear_reserva(
            cancha, date(2026, 1, 5), time(14, 0), time(15, 0), estado=EstadoReserva.SENADA,
            monto_sena=Decimal('11400.00'), monto_pagado=Decimal('11400.00'),
            transferencia_titular=TITULAR, transferencia_referencia=REFERENCIA,
        )
        jugador.estado = EstadoUsuario.BAJA
        jugador.save()

        borradas = ReservaRepository.limpiar_contactos_de_bajas_hasta(date(2026, 2, 1))

        assert borradas == 1
        reserva.refresh_from_db()
        assert reserva.transferencia_titular == ''
        assert reserva.transferencia_referencia == REFERENCIA

    def test_no_toca_a_quien_sigue_con_la_cuenta_activa(self, jugador, cancha, crear_reserva):
        reserva = crear_reserva(
            cancha, date(2026, 1, 5), time(14, 0), time(15, 0), transferencia_titular=TITULAR,
        )

        assert ReservaRepository.limpiar_contactos_de_bajas_hasta(date(2026, 2, 1)) == 0
        reserva.refresh_from_db()
        assert reserva.transferencia_titular == TITULAR
