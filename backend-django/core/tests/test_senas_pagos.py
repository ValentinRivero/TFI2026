from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from rest_framework import status

from conftest import HOY_CONGELADO
from core.models import (
    DiaSemana,
    EstadoPago,
    EstadoReserva,
    LogAuditoria,
    Reserva,
    TipoEventoAuditoria,
)
from core.serializers import validar_alias
from core.services import calcular_monto_sena
from core.tests.test_avisos_reservas import avisos  # noqa: F401

HOY = HOY_CONGELADO
MARTES = HOY + timedelta(days=1)

URL_RESERVAS = '/api/reservas/'
URL_MIAS = '/api/reservas/mias/'
URL_AGENDA = '/api/agenda/'
ALIAS = 'YACARE.TEST.SENA'


def _complejo_url(complejo):
    return f'/api/complejos/{complejo.id}/'


def _accion(reserva, nombre):
    return f'{URL_AGENDA}{reserva.id}/{nombre}/'


@pytest.fixture
def con_sena(complejo):
    complejo.porcentaje_sena = 30
    complejo.alias_transferencia = ALIAS
    complejo.titular_transferencia = 'Titular de Prueba'
    complejo.save()
    return complejo


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def reservar(reloj, jugador, cliente_de):
    def _reservar(cancha, hora='14:00'):
        return cliente_de(jugador).post(
            URL_RESERVAS, {'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': hora}, format='json',
        )

    return _reservar


@pytest.fixture
def reserva_con_sena(con_sena, cancha, crear_reserva):
    return crear_reserva(
        cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE,
        precio_acordado=Decimal('38000.00'), monto_sena=Decimal('11400.00'),
    )


class TestCalculoDeMontos:
    @pytest.mark.parametrize('precio,porcentaje,esperado', [
        ('38000.00', 30, '11400.00'),
        ('38000.00', 0, '0.00'),
        ('38000.00', 100, '38000.00'),
        ('1000.00', 33, '330.00'),
        ('100.05', 50, '50.03'),
        ('100.01', 50, '50.01'),
        ('0.01', 50, '0.01'),
        ('0.00', 40, '0.00'),
        ('19999.99', 15, '3000.00'),
        ('33333.33', 7, '2333.33'),
    ])
    def test_redondea_al_centavo_con_la_mitad_hacia_arriba(self, precio, porcentaje, esperado):
        assert calcular_monto_sena(Decimal(precio), porcentaje) == Decimal(esperado)

    def test_devuelve_decimal_con_dos_decimales_y_nunca_float(self):
        monto = calcular_monto_sena(Decimal('12345.67'), 33)

        assert isinstance(monto, Decimal)
        assert monto.as_tuple().exponent == -2


class TestValidacionDelAlias:
    @pytest.mark.parametrize('valor,esperado', [
        ('yacare.test-sena', 'YACARE.TEST-SENA'),
        ('Alias.Valido', 'ALIAS.VALIDO'),
        ('ABC123', 'ABC123'),
        ('a' * 20, 'A' * 20),
        ('', ''),
    ])
    def test_normaliza_a_mayusculas_y_acepta_el_formato(self, valor, esperado):
        assert validar_alias(valor) == esperado

    @pytest.mark.parametrize('valor', ['ab.c', 'a' * 21, 'con espacio', 'ñandu.pago', 'alias_bajo', 'ali@s.mp', 'a/b.cdef'])
    def test_rechaza_largo_o_caracteres_invalidos(self, valor):
        from rest_framework import serializers

        with pytest.raises(serializers.ValidationError):
            validar_alias(valor)


class TestConfiguracionDeSena:
    def _patch(self, cliente, complejo, datos):
        return cliente.patch(_complejo_url(complejo), datos, format='json')

    def test_el_dueno_configura_porcentaje_alias_y_titular(self, dueno, complejo, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo, {
            'porcentaje_sena': 30, 'alias_transferencia': 'cancha.goya.pago', 'titular_transferencia': 'Club de Prueba',
        })

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert (cuerpo['porcentaje_sena'], cuerpo['alias_transferencia']) == (30, 'CANCHA.GOYA.PAGO')
        assert cuerpo['titular_transferencia'] == 'Club de Prueba'
        complejo.refresh_from_db()
        assert complejo.alias_transferencia == 'CANCHA.GOYA.PAGO'

    def test_exigir_sena_sin_alias_responde_400(self, dueno, complejo, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo, {'porcentaje_sena': 20})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'alias_transferencia' in respuesta.json()['detail']
        complejo.refresh_from_db()
        assert complejo.porcentaje_sena == 0

    def test_no_se_puede_borrar_el_alias_mientras_se_exige_sena(self, dueno, con_sena, cliente_de):
        respuesta = self._patch(cliente_de(dueno), con_sena, {'alias_transferencia': ''})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        con_sena.refresh_from_db()
        assert con_sena.alias_transferencia == ALIAS

    def test_se_puede_quitar_la_sena_y_el_alias_en_el_mismo_pedido(self, dueno, con_sena, cliente_de):
        respuesta = self._patch(cliente_de(dueno), con_sena, {'porcentaje_sena': 0, 'alias_transferencia': ''})

        assert respuesta.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('campo,valor', [
        ('porcentaje_sena', 101),
        ('porcentaje_sena', -1),
        ('porcentaje_sena', 'treinta'),
        ('alias_transferencia', 'con espacio'),
        ('alias_transferencia', 'corto'),
        ('alias_transferencia', 'x' * 21),
        ('titular_transferencia', 'x' * 121),
    ])
    def test_valores_invalidos_responden_400(self, dueno, complejo, cliente_de, campo, valor):
        datos = {'porcentaje_sena': 0, campo: valor}

        assert self._patch(cliente_de(dueno), complejo, datos).status_code == status.HTTP_400_BAD_REQUEST

    def test_limpia_el_html_del_titular_y_del_alias(self, dueno, complejo, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo, {
            'titular_transferencia': '<script>alert(1)</script>Club Goya',
        })

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['titular_transferencia'] == 'Club Goya'
        assert self._patch(cliente_de(dueno), complejo, {'alias_transferencia': '<b>alias.ok1</b>'}).json()[
            'alias_transferencia'
        ] == 'ALIAS.OK1'

    def test_el_operador_no_configura_la_sena(self, operador, complejo, cliente_de):
        respuesta = self._patch(cliente_de(operador), complejo, {'porcentaje_sena': 10, 'alias_transferencia': ALIAS})

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN

    def test_un_dueno_ajeno_no_configura_el_complejo(self, dueno, complejo_ajeno, cliente_de):
        respuesta = self._patch(cliente_de(dueno), complejo_ajeno, {'porcentaje_sena': 10, 'alias_transferencia': ALIAS})

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_sin_sesion_responde_401(self, cliente, complejo):
        assert self._patch(cliente, complejo, {'porcentaje_sena': 0}).status_code == status.HTTP_401_UNAUTHORIZED

    def test_audita_el_cambio_sin_guardar_el_alias(self, dueno, complejo, cliente_de):
        self._patch(cliente_de(dueno), complejo, {'porcentaje_sena': 25, 'alias_transferencia': 'ALIAS.SECRETO'})

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.CAMBIO_CONFIGURACION)
        assert log.detalle == 'Campos modificados: alias_transferencia, porcentaje_sena.'
        assert 'SECRETO' not in log.detalle
        assert log.complejo_id == complejo.id

    def test_la_base_rechaza_una_sena_sin_alias(self, complejo):
        complejo.porcentaje_sena = 10
        complejo.alias_transferencia = ''

        with pytest.raises(IntegrityError), transaction.atomic():
            complejo.save()

    def test_el_catalogo_publico_expone_el_porcentaje_pero_no_el_alias(self, cliente, con_sena, cancha):
        cuerpo = cliente.get(_complejo_url(con_sena)).json()

        assert cuerpo['porcentaje_sena'] == 30
        assert 'alias_transferencia' not in cuerpo and 'titular_transferencia' not in cuerpo
        assert ALIAS not in str(cliente.get('/api/complejos/').json())


class TestCongelamientoDeMontosAlReservar:
    def test_con_sena_nace_pendiente_con_el_monto_calculado(self, reservar, con_sena, cancha):
        respuesta = reservar(cancha)

        assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['estado'] == EstadoReserva.PENDIENTE
        assert cuerpo['precio_acordado'] == '38000.00'
        assert cuerpo['monto_sena'] == '11400.00'
        assert cuerpo['monto_pagado'] == '0.00'
        assert cuerpo['saldo_restante'] == '38000.00'
        assert cuerpo['estado_pago'] == EstadoPago.SENA_PENDIENTE
        assert cuerpo['estado_pago_nombre'] == 'Seña pendiente'

    def test_el_jugador_recibe_los_datos_de_transferencia_si_hay_sena_pendiente(self, reservar, con_sena, cancha):
        cuerpo = reservar(cancha).json()

        assert cuerpo['datos_transferencia'] == {'alias': ALIAS, 'titular': 'Titular de Prueba'}

    def test_sin_sena_mantiene_el_comportamiento_actual(self, reservar, complejo, cancha):
        cuerpo = reservar(cancha).json()

        assert cuerpo['estado'] == EstadoReserva.PENDIENTE
        assert cuerpo['monto_sena'] == '0.00' and cuerpo['monto_pagado'] == '0.00'
        assert cuerpo['estado_pago'] == EstadoPago.SIN_SENA
        assert cuerpo['datos_transferencia'] is None

    def test_un_cambio_posterior_de_porcentaje_o_precio_no_altera_la_reserva(
        self, reservar, con_sena, cancha, dueno, cliente_de,
    ):
        reserva_id = reservar(cancha).json()['id']

        cliente_de(dueno).patch(_complejo_url(con_sena), {'porcentaje_sena': 80}, format='json')
        cancha.precio_base = Decimal('90000.00')
        cancha.save()

        reserva = Reserva.objects.get(pk=reserva_id)
        assert (reserva.precio_acordado, reserva.monto_sena) == (Decimal('38000.00'), Decimal('11400.00'))

    def test_una_reserva_nueva_usa_el_porcentaje_vigente(self, reservar, con_sena, cancha, dueno, cliente_de):
        cliente_de(dueno).patch(_complejo_url(con_sena), {'porcentaje_sena': 50}, format='json')

        assert reservar(cancha, '15:00').json()['monto_sena'] == '19000.00'

    def test_la_reserva_manual_tambien_congela_la_sena(self, reloj, dueno, con_sena, cancha, cliente_de):
        respuesta = cliente_de(dueno).post(URL_AGENDA, {
            'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '16:00',
            'nombre_cliente_manual': 'Rosendo Aquino',
        }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED, respuesta.json()
        assert respuesta.json()['monto_sena'] == '11400.00'

    def test_el_precio_diferenciado_es_la_base_de_la_sena(self, reloj, jugador, con_sena, crear_cancha, crear_horario, cliente_de):
        cancha = crear_cancha(con_sena, 'Cancha Nocturna')
        crear_horario(cancha, DiaSemana.MARTES, time(18, 0), time(23, 0), precio=Decimal('45000.50'))

        cuerpo = cliente_de(jugador).post(URL_RESERVAS, {
            'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '18:00',
        }, format='json').json()

        assert cuerpo['precio_acordado'] == '45000.50'
        assert cuerpo['monto_sena'] == '13500.15'

    def test_mis_reservas_muestra_el_desglose_y_el_alias_solo_con_sena_pendiente(
        self, reservar, con_sena, cancha, jugador, cliente_de,
    ):
        reservar(cancha)

        (reserva,) = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert reserva['monto_sena'] == '11400.00'
        assert reserva['datos_transferencia']['alias'] == ALIAS

    def test_el_alias_deja_de_viajar_cuando_la_sena_se_abona(
        self, reservar, con_sena, cancha, jugador, dueno, cliente_de,
    ):
        reserva_id = reservar(cancha).json()['id']
        cliente_de(dueno).post(f'{URL_AGENDA}{reserva_id}/confirmar-sena/')

        (reserva,) = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert reserva['estado_pago'] == EstadoPago.SENA_ABONADA
        assert reserva['datos_transferencia'] is None

    def test_las_reservas_anteriores_a_la_migracion_quedan_sin_sena(self, crear_reserva, cancha):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0))

        assert (reserva.monto_sena, reserva.monto_pagado) == (Decimal('0'), Decimal('0'))
        assert reserva.estado_pago == EstadoPago.SIN_SENA


class TestConfirmarSena:
    def test_el_dueno_confirma_la_sena_y_la_reserva_queda_senada(self, reloj, dueno, reserva_con_sena, cliente_de):
        respuesta = cliente_de(dueno).post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['estado'] == EstadoReserva.SENADA
        assert cuerpo['monto_pagado'] == '11400.00'
        assert cuerpo['saldo_restante'] == '26600.00'
        assert cuerpo['estado_pago'] == EstadoPago.SENA_ABONADA
        assert (cuerpo['puede_confirmar_sena'], cuerpo['puede_registrar_pago']) == (False, True)

    def test_el_operador_tambien_puede_confirmarla(self, reloj, operador, reserva_con_sena, cliente_de):
        respuesta = cliente_de(operador).post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_200_OK

    def test_el_superadmin_la_confirma_en_cualquier_complejo(self, reloj, superadmin, reserva_con_sena, cliente_de):
        assert cliente_de(superadmin).post(_accion(reserva_con_sena, 'confirmar-sena')).status_code == 200

    def test_funciona_desde_confirmada(self, reloj, dueno, reserva_con_sena, cliente_de):
        reserva_con_sena.estado = EstadoReserva.CONFIRMADA
        reserva_con_sena.save()

        respuesta = cliente_de(dueno).post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.json()['estado'] == EstadoReserva.SENADA

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE,
        EstadoReserva.COMPLETADA, EstadoReserva.SENADA,
    ])
    def test_rechaza_un_estado_que_no_admite_la_sena(self, reloj, dueno, reserva_con_sena, cliente_de, estado):
        reserva_con_sena.estado = estado
        reserva_con_sena.save()

        respuesta = cliente_de(dueno).post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        reserva_con_sena.refresh_from_db()
        assert reserva_con_sena.monto_pagado == 0

    def test_rechaza_registrar_dos_veces_la_misma_sena(self, reloj, dueno, reserva_con_sena, cliente_de):
        api = cliente_de(dueno)
        api.post(_accion(reserva_con_sena, 'confirmar-sena'))

        respuesta = api.post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ya está registrada' in respuesta.json()['detail']

    def test_rechaza_una_reserva_que_no_exige_sena(self, reloj, dueno, cancha, crear_reserva, cliente_de):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE)

        respuesta = cliente_de(dueno).post(_accion(reserva, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail'] == 'Esta reserva no exige seña: confirmala o registrá el pago total.'

    def test_audita_el_cobro_sin_datos_personales(self, reloj, dueno, reserva_con_sena, cliente_de):
        cliente_de(dueno).post(_accion(reserva_con_sena, 'confirmar-sena'))

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_PAGO)
        assert log.accion == 'Seña de reserva confirmada'
        assert log.usuario_id == dueno.id and log.complejo_id == reserva_con_sena.cancha.complejo_id
        assert 'Abonado: 11400.00 de 38000.00' in log.detalle
        assert 'Jugador Prueba' not in log.detalle and ALIAS not in log.detalle

    def test_avisa_al_titular_y_al_resto_del_personal(
        self, reloj, operador, jugador, dueno, reserva_con_sena, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(operador).post(_accion(reserva_con_sena, 'confirmar-sena'))

        al_personal, al_titular = entregados
        assert al_personal['usuarios_ids'] == [dueno.id]
        assert 'se registró la seña' in al_personal['mensaje']
        assert al_titular['usuario_id'] == jugador.id
        assert 'Tu turno quedó señado' in al_titular['mensaje']
        for aviso in entregados:
            assert jugador.nombre_completo not in aviso['mensaje'] and ALIAS not in aviso['mensaje']

    def test_una_reserva_de_otro_complejo_responde_404(self, reloj, dueno, complejo_ajeno, crear_cancha, crear_reserva, cliente_de):
        cancha_ajena = crear_cancha(complejo_ajeno, 'Ajena')
        ajena = crear_reserva(
            cancha_ajena, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE,
            precio_acordado=Decimal('1000.00'), monto_sena=Decimal('300.00'),
        )

        assert cliente_de(dueno).post(_accion(ajena, 'confirmar-sena')).status_code == status.HTTP_404_NOT_FOUND
        ajena.refresh_from_db()
        assert ajena.monto_pagado == 0

    def test_el_operador_de_otro_complejo_no_la_confirma(
        self, reloj, crear_usuario, complejo_ajeno, reserva_con_sena, cliente_de,
    ):
        operador_ajeno = crear_usuario('operador.ajeno@talibre.test', 'OPERADOR_COMPLEJO', complejo_operado=complejo_ajeno)

        respuesta = cliente_de(operador_ajeno).post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_el_jugador_no_puede_confirmar_su_propia_sena(self, reloj, jugador, reserva_con_sena, cliente_de):
        respuesta = cliente_de(jugador).post(_accion(reserva_con_sena, 'confirmar-sena'))

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        reserva_con_sena.refresh_from_db()
        assert reserva_con_sena.monto_pagado == 0

    def test_sin_sesion_responde_401(self, cliente, reserva_con_sena):
        assert cliente.post(_accion(reserva_con_sena, 'confirmar-sena')).status_code == status.HTTP_401_UNAUTHORIZED


class TestRegistrarPagoTotal:
    def test_salda_una_reserva_senada(self, reloj, dueno, reserva_con_sena, cliente_de):
        api = cliente_de(dueno)
        api.post(_accion(reserva_con_sena, 'confirmar-sena'))

        respuesta = api.post(_accion(reserva_con_sena, 'registrar-pago'))

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['estado'] == EstadoReserva.SENADA
        assert (cuerpo['monto_pagado'], cuerpo['saldo_restante']) == ('38000.00', '0.00')
        assert cuerpo['estado_pago'] == EstadoPago.PAGADA
        assert (cuerpo['puede_confirmar_sena'], cuerpo['puede_registrar_pago']) == (False, False)

    def test_desde_pendiente_paga_todo_y_queda_senada_pagada(self, reloj, dueno, reserva_con_sena, cliente_de):
        cuerpo = cliente_de(dueno).post(_accion(reserva_con_sena, 'registrar-pago')).json()

        assert cuerpo['estado'] == EstadoReserva.SENADA
        assert cuerpo['estado_pago'] == EstadoPago.PAGADA

    def test_sin_sena_una_pendiente_pasa_a_confirmada_y_queda_pagada(self, reloj, dueno, cancha, crear_reserva, cliente_de):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE)

        cuerpo = cliente_de(dueno).post(_accion(reserva, 'registrar-pago')).json()

        assert cuerpo['estado'] == EstadoReserva.CONFIRMADA
        assert cuerpo['estado_pago'] == EstadoPago.PAGADA and cuerpo['monto_pagado'] == '38000.00'
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_PAGO)
        assert 'Pendiente Seña -> Confirmada' in log.detalle

    @pytest.mark.parametrize('estado', [EstadoReserva.CONFIRMADA, EstadoReserva.COMPLETADA])
    def test_sin_sena_conserva_el_estado_operativo(self, reloj, dueno, cancha, crear_reserva, cliente_de, estado):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=estado)

        cuerpo = cliente_de(dueno).post(_accion(reserva, 'registrar-pago')).json()

        assert cuerpo['estado'] == estado and cuerpo['estado_pago'] == EstadoPago.PAGADA

    def test_sin_sena_nunca_deja_la_reserva_senada(self, reloj, dueno, cancha, crear_reserva, cliente_de):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE)

        cliente_de(dueno).post(_accion(reserva, 'registrar-pago'))

        reserva.refresh_from_db()
        assert reserva.estado != EstadoReserva.SENADA

    def test_saldar_una_completada_conserva_el_estado(self, reloj, dueno, reserva_con_sena, cliente_de):
        reserva_con_sena.estado = EstadoReserva.COMPLETADA
        reserva_con_sena.save()

        cuerpo = cliente_de(dueno).post(_accion(reserva_con_sena, 'registrar-pago')).json()

        assert cuerpo['estado'] == EstadoReserva.COMPLETADA and cuerpo['estado_pago'] == EstadoPago.PAGADA

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.CANCELADA_COMPLEJO, EstadoReserva.AUSENTE,
    ])
    def test_rechaza_cobrar_una_reserva_cancelada_o_ausente(self, reloj, dueno, reserva_con_sena, cliente_de, estado):
        reserva_con_sena.estado = estado
        reserva_con_sena.save()

        respuesta = cliente_de(dueno).post(_accion(reserva_con_sena, 'registrar-pago'))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        reserva_con_sena.refresh_from_db()
        assert reserva_con_sena.monto_pagado == 0

    def test_rechaza_cobrar_una_reserva_ya_saldada(self, reloj, dueno, reserva_con_sena, cliente_de):
        api = cliente_de(dueno)
        api.post(_accion(reserva_con_sena, 'registrar-pago'))

        respuesta = api.post(_accion(reserva_con_sena, 'registrar-pago'))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail'] == 'La reserva ya está saldada.'

    def test_avisa_que_el_turno_quedo_pagado(self, reloj, dueno, jugador, reserva_con_sena, cliente_de, avisos):
        with avisos as entregados:
            cliente_de(dueno).post(_accion(reserva_con_sena, 'registrar-pago'))

        assert 'Tu turno quedó pagado' in entregados[-1]['mensaje']
        assert entregados[-1]['usuario_id'] == jugador.id

    def test_audita_el_pago_total(self, reloj, dueno, reserva_con_sena, cliente_de):
        cliente_de(dueno).post(_accion(reserva_con_sena, 'registrar-pago'))

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.RESERVA_PAGO)
        assert log.accion == 'Pago total de reserva registrado'
        assert 'Abonado: 38000.00 de 38000.00' in log.detalle

    def test_el_jugador_y_el_anonimo_no_cobran(self, reloj, jugador, cliente, reserva_con_sena, cliente_de):
        assert cliente_de(jugador).post(_accion(reserva_con_sena, 'registrar-pago')).status_code == 403
        assert cliente.post(_accion(reserva_con_sena, 'registrar-pago')).status_code == 401

    def test_un_dueno_ajeno_no_cobra_reservas_de_otro_complejo(self, reloj, otro_dueno, reserva_con_sena, cliente_de):
        respuesta = cliente_de(otro_dueno).post(_accion(reserva_con_sena, 'registrar-pago'))

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND


class TestCoherenciaConLaAgenda:
    def test_pasar_a_senada_por_la_agenda_deja_abonada_la_sena(self, reloj, dueno, reserva_con_sena, cliente_de):
        respuesta = cliente_de(dueno).patch(
            f'{URL_AGENDA}{reserva_con_sena.id}/', {'estado': EstadoReserva.SENADA}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['monto_pagado'] == '11400.00'

    @pytest.mark.parametrize('anterior', [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA])
    def test_sin_sena_no_se_puede_pasar_a_senada_por_patch(self, reloj, dueno, cancha, crear_reserva, cliente_de, anterior):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=anterior)

        respuesta = cliente_de(dueno).patch(f'{URL_AGENDA}{reserva.id}/', {'estado': EstadoReserva.SENADA}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'estado' in respuesta.json()['detail']
        reserva.refresh_from_db()
        assert (reserva.estado, reserva.monto_pagado) == (anterior, 0)

    def test_sin_sena_si_se_puede_confirmar_o_cerrar_por_patch(self, reloj, dueno, cancha, crear_reserva, cliente_de):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE)

        respuesta = cliente_de(dueno).patch(f'{URL_AGENDA}{reserva.id}/', {'estado': EstadoReserva.CONFIRMADA}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK

    def test_una_senada_antigua_sin_montos_sigue_pudiendo_cerrarse(self, reloj, dueno, cancha, crear_reserva, cliente_de):
        reserva = crear_reserva(cancha, HOY - timedelta(days=1), time(14, 0), time(15, 0), estado=EstadoReserva.SENADA)

        respuesta = cliente_de(dueno).patch(f'{URL_AGENDA}{reserva.id}/', {'estado': EstadoReserva.COMPLETADA}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK

    def test_sin_sena_no_se_reabre_como_senada_pero_si_como_confirmada(self, reloj, dueno, cancha, crear_reserva, cliente_de):
        reserva = crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.CANCELADA_COMPLEJO)
        api = cliente_de(dueno)

        rechazada = api.post(
            f'{URL_AGENDA}{reserva.id}/reabrir/', {'estado': EstadoReserva.SENADA, 'confirmar': True}, format='json',
        )
        aceptada = api.post(
            f'{URL_AGENDA}{reserva.id}/reabrir/', {'estado': EstadoReserva.CONFIRMADA, 'confirmar': True}, format='json',
        )

        assert rechazada.status_code == status.HTTP_400_BAD_REQUEST
        assert aceptada.status_code == status.HTTP_200_OK and aceptada.json()['estado'] == EstadoReserva.CONFIRMADA

    def test_reabrir_como_senada_deja_abonada_la_sena(self, reloj, dueno, reserva_con_sena, cliente_de):
        reserva_con_sena.estado = EstadoReserva.CANCELADA_COMPLEJO
        reserva_con_sena.save()

        respuesta = cliente_de(dueno).post(
            f'{URL_AGENDA}{reserva_con_sena.id}/reabrir/', {'estado': EstadoReserva.SENADA, 'confirmar': True}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        assert respuesta.json()['monto_pagado'] == '11400.00'

    def test_la_agenda_lista_los_montos_sin_consultas_extra_por_fila(
        self, reloj, dueno, con_sena, cancha, crear_reserva, cliente_de, django_assert_max_num_queries,
    ):
        for hora in range(14, 20):
            crear_reserva(
                cancha, MARTES, time(hora, 0), time(hora + 1, 0), estado=EstadoReserva.PENDIENTE,
                monto_sena=Decimal('11400.00'),
            )
        api = cliente_de(dueno)
        api.get(URL_AGENDA)

        with django_assert_max_num_queries(20):
            respuesta = api.get(URL_AGENDA)

        assert respuesta.json()['count'] == 6
        assert all(reserva['estado_pago'] == EstadoPago.SENA_PENDIENTE for reserva in respuesta.json()['results'])

    def test_la_base_rechaza_montos_mayores_al_precio(self, cancha, crear_reserva):
        with pytest.raises(IntegrityError), transaction.atomic():
            crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), monto_sena=Decimal('38000.01'))

        with pytest.raises(IntegrityError), transaction.atomic():
            crear_reserva(cancha, MARTES, time(15, 0), time(16, 0), monto_pagado=Decimal('38000.01'))


class TestEstadoDePago:
    @pytest.mark.parametrize('precio,sena,pagado,esperado', [
        ('1000.00', '0.00', '0.00', EstadoPago.SIN_SENA),
        ('1000.00', '300.00', '0.00', EstadoPago.SENA_PENDIENTE),
        ('1000.00', '300.00', '299.99', EstadoPago.SENA_PENDIENTE),
        ('1000.00', '300.00', '300.00', EstadoPago.SENA_ABONADA),
        ('1000.00', '300.00', '999.99', EstadoPago.SENA_ABONADA),
        ('1000.00', '300.00', '1000.00', EstadoPago.PAGADA),
        ('1000.00', '0.00', '1000.00', EstadoPago.PAGADA),
        ('0.00', '0.00', '0.00', EstadoPago.SIN_SENA),
    ])
    def test_se_deduce_de_los_montos(self, cancha, crear_reserva, precio, sena, pagado, esperado):
        reserva = crear_reserva(
            cancha, MARTES, time(14, 0), time(15, 0), precio_acordado=Decimal(precio), monto_sena=Decimal(sena),
            monto_pagado=Decimal(pagado),
        )

        assert reserva.estado_pago == esperado
        assert reserva.saldo_restante == Decimal(precio) - Decimal(pagado)
