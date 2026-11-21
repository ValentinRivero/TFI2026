from decimal import Decimal

import pytest
from rest_framework import status

from core.models import (
    EstadoPago,
    EstadoReserva,
    LogAuditoria,
    MotivoRechazoTransferencia,
    TipoEventoAuditoria,
)
from core.services import PRIORIDAD_AVISO_URGENTE, AvisoComplejoService
from core.tests.test_avisos_reservas import avisos  # noqa: F401
from core.tests.test_transferencias import (  # noqa: F401
    REFERENCIA,
    TITULAR,
    URL_AGENDA,
    URL_MIAS,
    _informar,
    cancha,
    con_sena,
    reserva,
)

NO_LLEGO = MotivoRechazoTransferencia.NO_LLEGO


def _rechazar(api, reserva, motivo=NO_LLEGO, **extra):
    return api.post(f'{URL_AGENDA}{reserva.id}/rechazar-transferencia/', {'motivo': motivo, **extra}, format='json')


def _anular(api, reserva):
    return api.post(f'{URL_AGENDA}{reserva.id}/anular-cobro/')


@pytest.fixture
def informada(reloj, jugador, cliente_de, reserva):
    _informar(cliente_de(jugador), reserva)
    return reserva


class TestRechazarTransferencia:
    def test_el_personal_rechaza_con_un_motivo_y_no_cambia_estado_ni_montos(self, reloj, dueno, cliente_de, informada):
        antes = (informada.estado, informada.monto_pagado)

        respuesta = _rechazar(cliente_de(dueno), informada, nota='Revisá el monto')

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['transferencia_rechazada'] is True
        assert cuerpo['transferencia']['rechazo']['motivo'] == NO_LLEGO
        assert cuerpo['transferencia']['rechazo']['motivo_nombre'] == NO_LLEGO.label
        assert cuerpo['transferencia']['rechazo']['nota'] == 'Revisá el monto'
        informada.refresh_from_db()
        assert (informada.estado, informada.monto_pagado) == antes

    def test_conserva_lo_informado_y_la_confirmacion_sigue_disponible(self, reloj, dueno, cliente_de, informada):
        cuerpo = _rechazar(cliente_de(dueno), informada).json()

        assert cuerpo['transferencia']['titular'] == TITULAR and cuerpo['transferencia']['referencia'] == REFERENCIA
        assert cuerpo['puede_confirmar_sena'] is True

    def test_el_operador_tambien_puede_rechazar(self, reloj, operador, cliente_de, informada):
        assert _rechazar(cliente_de(operador), informada).status_code == status.HTTP_200_OK

    def test_el_jugador_ve_el_motivo_y_la_nota_en_su_reserva(self, reloj, jugador, dueno, cliente_de, informada):
        _rechazar(cliente_de(dueno), informada, MotivoRechazoTransferencia.MONTO_INCORRECTO, nota='Faltan $1.000')

        (fila,) = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert fila['transferencia_rechazada'] is True
        assert fila['transferencia']['rechazo']['motivo'] == MotivoRechazoTransferencia.MONTO_INCORRECTO
        assert fila['transferencia']['rechazo']['nota'] == 'Faltan $1.000'
        assert fila['datos_transferencia']['alias']  # sigue viendo el alias para transferir de nuevo

    def test_la_nota_se_limpia_y_tiene_tope(self, reloj, dueno, cliente_de, informada):
        api = cliente_de(dueno)

        limpia = _rechazar(api, informada, nota='<b>Revisá</b> <script>x</script>el monto')
        assert limpia.json()['transferencia']['rechazo']['nota'] == 'Revisá el monto'

    @pytest.mark.parametrize('extra', [{'nota': 'x' * 121}, {'motivo': 99}, {'motivo': 'otro'}, {'motivo': None}])
    def test_datos_invalidos_responden_400(self, reloj, dueno, cliente_de, informada, extra):
        datos = {'motivo': NO_LLEGO, **extra}

        respuesta = cliente_de(dueno).post(f'{URL_AGENDA}{informada.id}/rechazar-transferencia/', datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        informada.refresh_from_db()
        assert not informada.transferencia_rechazada

    def test_sin_transferencia_informada_responde_400(self, reloj, dueno, cliente_de, reserva):
        respuesta = _rechazar(cliente_de(dueno), reserva)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'no informó' in respuesta.json()['detail']

    def test_rechazar_dos_veces_responde_400(self, reloj, dueno, cliente_de, informada):
        api = cliente_de(dueno)
        _rechazar(api, informada)

        assert _rechazar(api, informada).status_code == status.HTTP_400_BAD_REQUEST

    def test_con_la_sena_ya_confirmada_responde_400(self, reloj, dueno, cliente_de, informada):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{informada.id}/confirmar-sena/')

        assert _rechazar(api, informada).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize('estado', [EstadoReserva.CANCELADA_JUGADOR, EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA])
    def test_con_la_reserva_cerrada_responde_400(self, reloj, dueno, cliente_de, informada, estado):
        informada.estado = estado
        informada.save()

        assert _rechazar(cliente_de(dueno), informada).status_code == status.HTTP_400_BAD_REQUEST

    def test_permisos_y_aislamiento(self, reloj, cliente, jugador, otro_dueno, cliente_de, informada):
        assert _rechazar(cliente, informada).status_code == status.HTTP_401_UNAUTHORIZED
        assert _rechazar(cliente_de(jugador), informada).status_code == status.HTTP_403_FORBIDDEN
        assert _rechazar(cliente_de(otro_dueno), informada).status_code == status.HTTP_404_NOT_FOUND
        informada.refresh_from_db()
        assert not informada.transferencia_rechazada


class TestAvisosYAuditoriaDelRechazo:
    def test_avisa_al_jugador_con_el_motivo_y_sin_datos_personales(
        self, reloj, jugador, dueno, cliente_de, informada, avisos,
    ):
        with avisos as entregados:
            _rechazar(cliente_de(dueno), informada, nota='Texto libre del complejo')

        al_jugador = next(aviso for aviso in entregados if aviso['usuario_id'] == jugador.id)
        assert al_jugador['prioridad'] == PRIORIDAD_AVISO_URGENTE
        assert NO_LLEGO.label in al_jugador['mensaje'] and 'Mis reservas' in al_jugador['mensaje']
        for aviso in entregados:
            texto = f"{aviso['mensaje']} {(aviso.get('registro') or {}).get('mensaje', '')}"
            for dato in (TITULAR, REFERENCIA, 'Texto libre', jugador.email):
                assert dato not in texto

    def test_avisa_al_resto_del_personal_menos_a_quien_rechazo(self, reloj, dueno, operador, cliente_de, informada, avisos):
        with avisos as entregados:
            _rechazar(cliente_de(operador), informada)

        al_personal = next(aviso for aviso in entregados if aviso.get('usuarios_ids'))
        assert al_personal['usuarios_ids'] == [dueno.id]
        assert 'se rechazó la transferencia informada' in al_personal['mensaje']

    def test_audita_el_motivo_sin_la_nota_ni_lo_informado(self, reloj, dueno, cliente_de, informada, con_sena):
        _rechazar(cliente_de(dueno), informada, nota='Texto libre del complejo')

        log = LogAuditoria.objects.filter(accion='Transferencia de seña rechazada').get()
        assert log.tipo_evento == TipoEventoAuditoria.TRANSFERENCIA_INFORMADA
        assert (log.usuario_id, log.complejo_id) == (dueno.id, con_sena.id)
        assert NO_LLEGO.label in log.detalle
        for dato in (TITULAR, REFERENCIA, 'Texto libre'):
            assert dato not in log.detalle


class TestVolverAInformar:
    def test_el_jugador_reenvia_y_se_limpia_el_rechazo(self, jugador, dueno, cliente_de, informada):
        _rechazar(cliente_de(dueno), informada)

        respuesta = _informar(cliente_de(jugador), informada, referencia='OP-99999')

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['transferencia_rechazada'] is False and cuerpo['transferencia']['rechazo'] is None
        assert cuerpo['transferencia']['referencia'] == 'OP-99999'

    def test_puede_reenviar_los_mismos_datos_tras_un_rechazo(self, reloj, jugador, dueno, cliente_de, informada, avisos):
        _rechazar(cliente_de(dueno), informada)

        with avisos as entregados:
            respuesta = _informar(cliente_de(jugador), informada)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['transferencia_rechazada'] is False
        assert 'volvió a informar la transferencia' in entregados[0]['mensaje']

    def test_audita_el_reenvio_como_tal(self, reloj, jugador, dueno, cliente_de, informada):
        _rechazar(cliente_de(dueno), informada)
        _informar(cliente_de(jugador), informada)

        acciones = list(LogAuditoria.objects.filter(
            tipo_evento=TipoEventoAuditoria.TRANSFERENCIA_INFORMADA).order_by('id').values_list('accion', flat=True))

        assert acciones == [
            'Transferencia de seña informada', 'Transferencia de seña rechazada',
            'Transferencia de seña informada de nuevo tras un rechazo',
        ]

    def test_despues_del_reenvio_se_puede_rechazar_de_nuevo(self, reloj, jugador, dueno, cliente_de, informada):
        _rechazar(cliente_de(dueno), informada)
        _informar(cliente_de(jugador), informada)

        assert _rechazar(cliente_de(dueno), informada).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('accion', ['confirmar-sena', 'registrar-pago'])
    def test_el_personal_puede_confirmar_igual_y_eso_limpia_el_rechazo(self, reloj, dueno, cliente_de, informada, accion):
        api = cliente_de(dueno)
        _rechazar(api, informada)

        respuesta = api.post(f'{URL_AGENDA}{informada.id}/{accion}/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['transferencia_rechazada'] is False
        assert respuesta.json()['transferencia']['rechazo'] is None


class TestAnularCobro:
    def test_el_dueno_anula_una_sena_y_la_reserva_vuelve_a_pendiente(self, reloj, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        respuesta = _anular(api, reserva)

        assert respuesta.status_code == status.HTTP_200_OK, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo['estado'] == EstadoReserva.PENDIENTE
        assert (cuerpo['monto_pagado'], cuerpo['saldo_restante']) == ('0.00', '38000.00')
        assert cuerpo['estado_pago'] == EstadoPago.SENA_PENDIENTE
        assert (cuerpo['puede_anular_cobro'], cuerpo['puede_confirmar_sena']) == (False, True)

    def test_anula_un_pago_total(self, reloj, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/registrar-pago/')

        cuerpo = _anular(api, reserva).json()

        assert cuerpo['monto_pagado'] == '0.00' and cuerpo['estado'] == EstadoReserva.PENDIENTE

    def test_el_superadmin_tambien_puede(self, reloj, superadmin, dueno, cliente_de, reserva):
        cliente_de(dueno).post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        assert _anular(cliente_de(superadmin), reserva).status_code == status.HTTP_200_OK

    def test_el_jugador_vuelve_a_ver_el_alias_para_transferir(self, reloj, jugador, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')
        _anular(api, reserva)

        (fila,) = cliente_de(jugador).get(URL_MIAS).json()['results']

        assert fila['datos_transferencia']['alias'] and fila['estado_pago'] == EstadoPago.SENA_PENDIENTE

    @pytest.mark.parametrize('estado', [
        EstadoReserva.CONFIRMADA, EstadoReserva.COMPLETADA, EstadoReserva.AUSENTE, EstadoReserva.CANCELADA_COMPLEJO,
    ])
    def test_otros_estados_conservan_su_estado_operativo(self, reloj, dueno, cliente_de, reserva, estado):
        reserva.estado = estado
        reserva.monto_pagado = reserva.monto_sena
        reserva.save()

        cuerpo = _anular(cliente_de(dueno), reserva).json()

        assert cuerpo['estado'] == estado and cuerpo['monto_pagado'] == '0.00'

    def test_una_reserva_sin_seña_senada_antigua_vuelve_a_confirmada(self, reloj, dueno, cliente_de, cancha, crear_reserva):
        from datetime import time

        from core.tests.test_transferencias import MARTES

        antigua = crear_reserva(
            cancha, MARTES, time(16, 0), time(17, 0), estado=EstadoReserva.SENADA, monto_pagado=Decimal('38000.00'),
        )

        assert _anular(cliente_de(dueno), antigua).json()['estado'] == EstadoReserva.CONFIRMADA

    def test_sin_cobro_registrado_responde_400(self, reloj, dueno, cliente_de, reserva):
        respuesta = _anular(cliente_de(dueno), reserva)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['detail'] == 'Esta reserva no tiene un cobro registrado.'

    def test_anular_dos_veces_responde_400(self, reloj, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')
        _anular(api, reserva)

        assert _anular(api, reserva).status_code == status.HTTP_400_BAD_REQUEST

    def test_solo_el_dueno_y_el_superadmin_tienen_el_permiso(
        self, reloj, cliente, jugador, operador, otro_dueno, cliente_de, reserva, dueno,
    ):
        cliente_de(dueno).post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        assert _anular(cliente, reserva).status_code == status.HTTP_401_UNAUTHORIZED
        assert _anular(cliente_de(jugador), reserva).status_code == status.HTTP_403_FORBIDDEN
        assert _anular(cliente_de(operador), reserva).status_code == status.HTTP_403_FORBIDDEN
        assert _anular(cliente_de(otro_dueno), reserva).status_code == status.HTTP_404_NOT_FOUND
        reserva.refresh_from_db()
        assert reserva.monto_pagado == reserva.monto_sena

    def test_el_indicador_de_la_agenda_sigue_al_monto_abonado(self, reloj, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        assert api.get(f'{URL_AGENDA}{reserva.id}/').json()['puede_anular_cobro'] is False

        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        assert api.get(f'{URL_AGENDA}{reserva.id}/').json()['puede_anular_cobro'] is True

    def test_es_reversible_se_vuelve_a_registrar_el_cobro(self, reloj, dueno, cliente_de, reserva):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')
        _anular(api, reserva)

        respuesta = api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoReserva.SENADA and respuesta.json()['monto_pagado'] == '11400.00'

    def test_se_puede_anular_y_rechazar_una_transferencia_que_no_llego(
        self, reloj, jugador, dueno, cliente_de, informada,
    ):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{informada.id}/confirmar-sena/')
        _anular(api, informada)

        respuesta = _rechazar(api, informada)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['transferencia_rechazada'] is True


class TestAvisosYAuditoriaDeLaAnulacion:
    def test_avisa_al_jugador_y_al_resto_del_personal(self, reloj, jugador, dueno, operador, cliente_de, reserva, avisos):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')

        with avisos as entregados:
            _anular(api, reserva)

        al_jugador = next(aviso for aviso in entregados if aviso['usuario_id'] == jugador.id)
        al_personal = next(aviso for aviso in entregados if aviso.get('usuarios_ids'))
        assert al_jugador['prioridad'] == PRIORIDAD_AVISO_URGENTE and 'dejó sin efecto el cobro' in al_jugador['mensaje']
        assert al_personal['usuarios_ids'] == [operador.id] and 'se anuló el cobro' in al_personal['mensaje']
        for aviso in entregados:
            assert jugador.nombre_completo not in aviso['mensaje'] and jugador.email not in aviso['mensaje']

    def test_audita_el_monto_anulado_y_los_estados(self, reloj, dueno, cliente_de, reserva, con_sena):
        api = cliente_de(dueno)
        api.post(f'{URL_AGENDA}{reserva.id}/confirmar-sena/')
        _anular(api, reserva)

        log = LogAuditoria.objects.get(accion='Cobro de reserva anulado')
        assert log.tipo_evento == TipoEventoAuditoria.RESERVA_PAGO
        assert (log.usuario_id, log.complejo_id) == (dueno.id, con_sena.id)
        assert 'Anulado: 11400.00 de 38000.00' in log.detalle
        assert 'Señada/Pagada -> Pendiente Seña' in log.detalle

    def test_un_rechazo_no_audita_ni_avisa(self, reloj, dueno, cliente_de, reserva, avisos):
        with avisos as entregados:
            _anular(cliente_de(dueno), reserva)

        assert entregados == []
        assert not LogAuditoria.objects.filter(accion='Cobro de reserva anulado').exists()


class TestTextoDelRegistro:
    def test_no_repite_el_id_cuando_el_titular_es_quien_hizo_el_cambio(self):
        texto = AvisoComplejoService._texto_de_registro('Aviso', {'cancha': 3, 'titular': 9}, 9)

        assert texto == 'Aviso (Cancha id 3; Titular y autor: usuario id 9)'

    def test_con_otro_autor_conserva_ambos_ids(self):
        texto = AvisoComplejoService._texto_de_registro('Aviso', {'cancha': 3, 'titular': 9}, 7)

        assert texto == 'Aviso (Cancha id 3; Titular: usuario id 9; Hecho por usuario id 7)'
