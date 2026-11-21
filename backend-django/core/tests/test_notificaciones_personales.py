"""
Cada aviso llega a la bandeja personal (`usuario_id`) de quien corresponde según su rol, su identificación con el
complejo y sus permisos: el jugador titular, el personal del complejo, solo el dueño en lo comercial y los
superadministradores en lo del sistema. Los avisos se capturan antes de salir hacia backend-node.
"""
from datetime import time, timedelta
from unittest import mock

from decimal import Decimal

import pytest
from django.db import DatabaseError
from rest_framework import status

from conftest import HOY_CONGELADO, PASSWORD_PRUEBA
from core.models import (
    DiaSemana,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    EstadoUsuario,
    RolPermiso,
    TipoMotivoExcepcion,
)
from core.services import (
    CATEGORIA_AVISO_CUENTAS,
    CATEGORIA_AVISO_OPERATORIA,
    CATEGORIA_AVISO_RESERVAS,
    CATEGORIA_AVISO_SISTEMA,
    PRIORIDAD_AVISO_NORMAL,
    PRIORIDAD_AVISO_URGENTE,
    AvisoComplejoService,
    DestinatariosService,
    ReservaService,
)

MARTES = HOY_CONGELADO + timedelta(days=1)


@pytest.fixture
def avisos(django_capture_on_commit_callbacks):
    """Junta los avisos que se habrían entregado a backend-node durante el bloque."""
    entregados = []

    class Captura:
        def __enter__(self):
            entregados.clear()
            self.parche = mock.patch.object(AvisoComplejoService, 'entregar', side_effect=entregados.append)
            self.parche.start()
            self.commit = django_capture_on_commit_callbacks(execute=True)
            self.commit.__enter__()
            return entregados

        def __exit__(self, *args):
            self.commit.__exit__(*args)
            self.parche.stop()

    return Captura()


@pytest.fixture(autouse=True)
def lunes_a_las_diez(reloj):
    return reloj


@pytest.fixture
def cancha(complejo, crear_cancha, crear_horario):
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return cancha


@pytest.fixture
def reserva(cancha, crear_reserva):
    return crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE, monto_sena=Decimal('11400.00'))


def _del_jugador(entregados, jugador):
    return [aviso for aviso in entregados if aviso['usuario_id'] == jugador.id]


def _personales(entregados):
    return [aviso for aviso in entregados if aviso['usuario_id'] or aviso['usuarios_ids']]


def _del_grupo(entregados, *usuarios):
    ids = sorted(usuario.id for usuario in usuarios)
    return [aviso for aviso in entregados if aviso['usuarios_ids'] == ids]


def _cambiar_estado(cliente_de, usuario, reserva, estado):
    return cliente_de(usuario).patch(f'/api/agenda/{reserva.id}/', {'estado': estado}, format='json')


def _empezo_el_turno(reloj):
    reloj.return_value = reloj.return_value.replace(day=17, hour=16)


class TestDestinatarios:
    def test_el_personal_es_el_dueno_y_los_operadores_activos_del_complejo(self, dueno, operador, complejo):
        assert DestinatariosService.personal(complejo, 'ver_agenda') == sorted([dueno.id, operador.id])

    def test_un_operador_suspendido_o_de_otro_complejo_no_recibe(
        self, dueno, operador, complejo, complejo_ajeno, crear_usuario,
    ):
        crear_usuario(
            'operador.ajeno@talibre.test', 'OPERADOR_COMPLEJO', complejo_operado=complejo_ajeno,
        )
        operador.estado = EstadoUsuario.SUSPENDIDO
        operador.save()

        assert DestinatariosService.personal(complejo, 'ver_agenda') == [dueno.id]

    def test_sin_el_permiso_en_su_rol_no_recibe(self, dueno, operador, complejo):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='ver_excepciones').desactivar()

        assert DestinatariosService.personal(complejo, 'ver_excepciones') == [dueno.id]
        assert DestinatariosService.personal(complejo, 'ver_agenda') == sorted([dueno.id, operador.id])

    def test_lo_comercial_es_solo_del_dueno_y_exige_el_permiso_del_rol(self, dueno, operador, complejo):
        assert DestinatariosService.dueno(complejo, 'configurar_complejo') == [dueno.id]
        RolPermiso.objects.get(rol__nombre='DUENO_COMPLEJO', permiso__codigo='configurar_complejo').desactivar()
        assert DestinatariosService.dueno(complejo, 'configurar_complejo') == []

    def test_quien_hizo_el_cambio_no_se_avisa_a_si_mismo(self, dueno, operador, complejo):
        assert DestinatariosService.personal(complejo, 'ver_agenda', excluir=operador) == [dueno.id]

    def test_los_superadmins_son_los_activos(self, superadmin, crear_usuario):
        suspendido = crear_usuario('superadmin.suspendido@talibre.test', 'SUPERADMIN')
        suspendido.estado = EstadoUsuario.SUSPENDIDO
        suspendido.save()

        assert DestinatariosService.superadmins() == [superadmin.id]


class TestAvisosAlJugador:
    def test_reserva_web_registrada_le_llega_pendiente_de_sena(self, jugador, dueno, cancha, cliente_de, avisos):
        with avisos as entregados:
            respuesta = cliente_de(jugador).post('/api/reservas/', {
                'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '16:00',
            }, format='json')

        (propio,) = _del_jugador(entregados, jugador)
        assert respuesta.status_code == status.HTTP_201_CREATED
        assert 'quedó registrada' in propio['mensaje'] and 'pendiente de seña' in propio['mensaje']
        assert cancha.complejo.nombre in propio['mensaje']
        assert (propio['categoria'], propio['prioridad']) == (CATEGORIA_AVISO_RESERVAS, PRIORIDAD_AVISO_NORMAL)

    def test_confirmada(self, jugador, operador, reserva, cliente_de, avisos):
        with avisos as entregados:
            respuesta = _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.CONFIRMADA)

        assert respuesta.status_code == status.HTTP_200_OK
        (propio,) = _del_jugador(entregados, jugador)
        assert 'confirmó tu reserva' in propio['mensaje']

    def test_senada_y_pagada_tienen_avisos_separados(self, jugador, operador, reserva, cliente_de, avisos):
        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.SENADA)
        (senada,) = _del_jugador(entregados, jugador)

        with avisos as entregados:
            ReservaService._avisar_reserva_pagada(reserva)
        (pagada,) = _del_jugador(entregados, jugador)

        assert 'registró la seña' in senada['mensaje'] and 'señado' in senada['mensaje']
        assert 'registró el pago' in pagada['mensaje'] and 'pagado' in pagada['mensaje']
        assert 'pago' not in senada['mensaje'] and 'seña' not in pagada['mensaje']

    @pytest.mark.parametrize('estado, texto', [
        (EstadoReserva.COMPLETADA, 'figura como completada'),
        (EstadoReserva.AUSENTE, 'figura como ausente'),
    ])
    def test_completada_y_ausente(self, reloj, jugador, operador, reserva, cliente_de, avisos, estado, texto):
        _empezo_el_turno(reloj)

        with avisos as entregados:
            respuesta = _cambiar_estado(cliente_de, operador, reserva, estado)

        assert respuesta.status_code == status.HTTP_200_OK
        (propio,) = _del_jugador(entregados, jugador)
        assert texto in propio['mensaje']

    def test_editar_solo_las_observaciones_no_avisa(self, jugador, operador, reserva, cliente_de, avisos):
        with avisos as entregados:
            respuesta = cliente_de(operador).patch(
                f'/api/agenda/{reserva.id}/', {'observaciones': 'Trae pelota propia.'}, format='json',
            )

        assert respuesta.status_code == status.HTTP_200_OK
        assert entregados == []

    def test_cancelacion_propia_confirma_y_la_del_complejo_es_urgente(
        self, jugador, operador, cancha, crear_reserva, cliente_de, avisos,
    ):
        propia = crear_reserva(cancha, MARTES, time(15, 0), time(16, 0))
        del_complejo = crear_reserva(cancha, MARTES, time(16, 0), time(17, 0))

        with avisos as entregados:
            cliente_de(jugador).post(f'/api/reservas/{propia.id}/cancelar/')
        (constancia,) = _del_jugador(entregados, jugador)
        with avisos as entregados:
            cliente_de(operador).post(f'/api/agenda/{del_complejo.id}/cancelar/')
        (urgente,) = _del_jugador(entregados, jugador)

        assert 'Procesamos la cancelación' in constancia['mensaje'] and constancia['prioridad'] == PRIORIDAD_AVISO_NORMAL
        assert 'canceló tu reserva' in urgente['mensaje'] and urgente['prioridad'] == PRIORIDAD_AVISO_URGENTE

    def test_reapertura_indica_en_que_estado_quedo(self, jugador, operador, reserva, cliente_de, avisos):
        reserva.estado = EstadoReserva.CANCELADA_COMPLEJO
        reserva.save()

        with avisos as entregados:
            respuesta = cliente_de(operador).post(
                f'/api/agenda/{reserva.id}/reabrir/', {'estado': EstadoReserva.SENADA, 'confirmar': True}, format='json',
            )

        assert respuesta.status_code == status.HTTP_200_OK
        (propio,) = _del_jugador(entregados, jugador)
        assert 'reabrió tu reserva' in propio['mensaje'] and '«Señada/Pagada»' in propio['mensaje']

    def test_fecha_de_turno_fijo_registrada_o_cancelada(self, jugador, operador, cancha, crear_turno_fijo, cliente_de, avisos):
        turno = crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(20, 0), time(21, 0), desde=MARTES, usuario=jugador,
            nombre_cliente_manual='', telefono_cliente_manual='',
        )
        url = f'/api/turnos-fijos/{turno.id}/fechas/'

        with avisos as entregados:
            cliente_de(operador).post(url, {'fecha_turno': MARTES.isoformat(), 'accion': 'mantener'}, format='json')
        (registrada,) = _del_jugador(entregados, jugador)
        with avisos as entregados:
            cliente_de(operador).post(
                url, {'fecha_turno': (MARTES + timedelta(days=7)).isoformat(), 'accion': 'cancelar'}, format='json',
            )
        (cancelada,) = _del_jugador(entregados, jugador)

        assert 'registró una fecha de tu turno fijo' in registrada['mensaje']
        assert 'canceló tu reserva' in cancelada['mensaje'] and cancelada['prioridad'] == PRIORIDAD_AVISO_URGENTE

    def test_una_excepcion_que_afecta_su_reserva_se_la_avisa_con_urgencia(
        self, jugador, dueno, operador, reserva, complejo, cliente_de, avisos,
    ):
        with avisos as entregados:
            respuesta = cliente_de(dueno).post('/api/excepciones/', {
                'complejo': complejo.id, 'cancha': None, 'fecha_inicio': MARTES.isoformat(),
                'fecha_fin': MARTES.isoformat(), 'es_dia_completo': 1, 'tipo_motivo': TipoMotivoExcepcion.FERIADO,
            }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        (propio,) = _del_jugador(entregados, jugador)
        assert propio['prioridad'] == PRIORIDAD_AVISO_URGENTE and f'tu reserva id {reserva.id}' in propio['mensaje']
        (para_el_personal,) = _del_grupo(entregados, operador)
        assert para_el_personal['categoria'] == CATEGORIA_AVISO_OPERATORIA
        assert para_el_personal['prioridad'] == PRIORIDAD_AVISO_URGENTE

    def test_una_excepcion_en_otra_franja_no_afecta_a_nadie(
        self, jugador, dueno, operador, reserva, complejo, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(dueno).post('/api/excepciones/', {
                'complejo': complejo.id, 'cancha': None, 'fecha_inicio': MARTES.isoformat(),
                'fecha_fin': MARTES.isoformat(), 'es_dia_completo': 0, 'hora_inicio': '18:00', 'hora_fin': '20:00',
                'tipo_motivo': TipoMotivoExcepcion.CLIMA,
            }, format='json')

        assert _del_jugador(entregados, jugador) == []
        (para_el_personal,) = entregados
        assert para_el_personal['prioridad'] == PRIORIDAD_AVISO_NORMAL

    def test_un_cambio_de_horario_confirmado_avisa_a_cada_titular_afectado(
        self, jugador, dueno, operador, cancha, reserva, crear_horario, cliente_de, avisos,
    ):
        horario = cancha.horarios.get()

        with avisos as entregados:
            respuesta = cliente_de(dueno).patch(
                f'/api/horarios/{horario.id}/', {'hora_apertura': '16:00', 'confirmar': True}, format='json',
            )

        assert respuesta.status_code == status.HTTP_200_OK
        (propio,) = _del_jugador(entregados, jugador)
        assert 'quedó fuera de la grilla' in propio['mensaje'] and propio['prioridad'] == PRIORIDAD_AVISO_URGENTE
        (personal,) = _del_grupo(entregados, dueno, operador)
        assert 'dejó fuera de la grilla' in personal['mensaje']

    def test_una_reserva_manual_no_tiene_a_quien_avisar_en_su_estado(
        self, operador, dueno, cancha, crear_reserva, cliente_de, avisos,
    ):
        manual = crear_reserva(cancha, MARTES, time(17, 0), time(18, 0), usuario=None, estado=EstadoReserva.PENDIENTE)

        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, manual, EstadoReserva.CONFIRMADA)

        assert [aviso['usuario_id'] for aviso in entregados] == [None]
        assert entregados[0]['usuarios_ids'] == [dueno.id]
        assert 'Titular' not in entregados[0]['registro']['mensaje']

    def test_los_avisos_al_jugador_no_exponen_datos_personales(self, jugador, operador, reserva, cliente_de, avisos):
        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.SENADA)

        for aviso in entregados:
            for dato in (jugador.email, jugador.telefono, operador.email, PASSWORD_PRUEBA):
                if dato:
                    assert dato not in aviso['mensaje']


class TestAvisosAlPersonalDelComplejo:
    def test_una_reserva_web_llega_al_dueno_y_a_cada_operador_con_el_nombre_del_complejo(
        self, jugador, dueno, operador, complejo, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(jugador).post('/api/reservas/', {
                'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '16:00',
            }, format='json')

        (personal,) = _del_grupo(entregados, dueno, operador)
        assert personal['complejo_id'] == complejo.id and personal['mensaje'].startswith(f'{complejo.nombre}: ')
        assert personal['evento'] is not None

    def test_un_cambio_de_estado_hecho_por_el_operador_le_llega_al_dueno_pero_no_a_el(
        self, dueno, operador, reserva, cliente_de, avisos,
    ):
        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.CONFIRMADA)

        (personal,) = _del_grupo(entregados, dueno)
        assert 'pasó de «Pendiente Seña» a «Confirmada»' in personal['mensaje']

    def test_la_baja_de_una_excepcion_se_avisa_al_resto_del_personal(
        self, dueno, operador, complejo, crear_excepcion_horaria, cliente_de, avisos,
    ):
        excepcion = crear_excepcion_horaria(complejo, MARTES)

        with avisos as entregados:
            respuesta = cliente_de(operador).delete(f'/api/excepciones/{excepcion.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        (personal,) = _del_grupo(entregados, dueno)
        assert 'se dio de baja la excepción' in personal['mensaje']

    def test_el_operador_sin_permiso_de_excepciones_no_las_recibe(
        self, dueno, operador, complejo, crear_excepcion_horaria, cliente_de, avisos,
    ):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='ver_excepciones').desactivar()
        excepcion = crear_excepcion_horaria(complejo, MARTES)

        with avisos as entregados:
            cliente_de(dueno).delete(f'/api/excepciones/{excepcion.id}/')

        assert _personales(entregados) == []

    def test_la_baja_de_cuenta_con_una_sena_va_solo_al_dueno_y_lo_operativo_a_todos(
        self, jugador, dueno, operador, cancha, crear_reserva, cliente_de, avisos,
    ):
        crear_reserva(cancha, MARTES, time(18, 0), time(19, 0), estado=EstadoReserva.SENADA)
        crear_reserva(cancha, MARTES, time(19, 0), time(20, 0), estado=EstadoReserva.CONFIRMADA)

        with avisos as entregados:
            respuesta = cliente_de(jugador).delete('/api/perfil/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        del_dueno = _del_grupo(entregados, dueno)
        del_personal = _del_grupo(entregados, dueno, operador)
        (seña,) = [aviso for aviso in del_dueno if aviso['prioridad'] == PRIORIDAD_AVISO_URGENTE]
        assert 'conserva 1 reserva señada' in seña['mensaje']
        assert [aviso['categoria'] for aviso in del_personal] == [CATEGORIA_AVISO_RESERVAS]
        assert 'se cancelaron 1 reserva' in del_personal[0]['mensaje']


class TestAvisosComercialesAlDueno:
    def test_un_cambio_de_configuracion_hecho_por_otro_llega_al_dueno(
        self, dueno, superadmin, complejo, cliente_de, avisos,
    ):
        with avisos as entregados:
            respuesta = cliente_de(superadmin).patch(
                f'/api/complejos/{complejo.id}/', {'horas_limite_cancelacion': 12}, format='json',
            )

        assert respuesta.status_code == status.HTTP_200_OK
        (aviso,) = _del_grupo(entregados, dueno)
        assert aviso['categoria'] == CATEGORIA_AVISO_OPERATORIA and 'horas_limite_cancelacion' in aviso['mensaje']

    def test_el_cambio_de_precio_hecho_por_el_propio_dueno_no_se_le_avisa(
        self, dueno, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(dueno).patch(f'/api/canchas/{cancha.id}/', {'precio_base': '41000'}, format='json')

        assert _personales(entregados) == []
        (registro,) = entregados
        assert registro['registro']['ambito'] == 2 and f'Hecho por usuario id {dueno.id}' in registro['registro']['mensaje']

    def test_el_cambio_de_precio_hecho_por_el_superadmin_llega_al_dueno_sin_operadores(
        self, dueno, operador, superadmin, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(superadmin).patch(f'/api/canchas/{cancha.id}/', {'precio_base': '41000'}, format='json')

        (aviso,) = entregados
        assert aviso['usuarios_ids'] == [dueno.id] and 'precio base' in aviso['mensaje']

    def test_el_precio_diferenciado_de_un_horario_llega_solo_al_dueno(
        self, dueno, operador, superadmin, cancha, cliente_de, avisos,
    ):
        horario = cancha.horarios.get()

        with avisos as entregados:
            cliente_de(superadmin).patch(
                f'/api/horarios/{horario.id}/', {'precio_diferenciado': '45000'}, format='json',
            )

        (aviso,) = entregados
        assert aviso['usuarios_ids'] == [dueno.id] and 'precio diferenciado' in aviso['mensaje']

    def test_el_cambio_de_contrato_llega_al_dueno(self, dueno, superadmin, complejo, cliente_de, avisos):
        with avisos as entregados:
            cliente_de(superadmin).patch(
                f'/api/contratos/{complejo.id}/', {'estado_contrato': EstadoContrato.SUSPENDIDO}, format='json',
            )

        (aviso,) = _del_grupo(entregados, dueno)
        assert aviso['prioridad'] == PRIORIDAD_AVISO_URGENTE and 'Activo -> Suspendido' in aviso['mensaje']


class TestVincularOperadores:
    def test_el_alta_y_la_baja_de_un_operador_las_hace_el_superadmin_y_llegan_al_dueno(
        self, dueno, superadmin, complejo, crear_usuario, cliente_de, avisos,
    ):
        nuevo = crear_usuario('operador.nuevo@talibre.test', 'OPERADOR_COMPLEJO')
        base = f'/api/complejos/{complejo.id}/operadores/'

        with avisos as entregados:
            alta = cliente_de(superadmin).post(base, {'email': nuevo.email}, format='json')
        (vinculado,) = _del_grupo(entregados, dueno)
        with avisos as entregados:
            baja = cliente_de(superadmin).delete(f'{base}{nuevo.id}/')
        (desvinculado,) = _del_grupo(entregados, dueno)

        assert alta.status_code == status.HTTP_201_CREATED and baja.status_code == status.HTTP_204_NO_CONTENT
        assert 'se vinculó' in vinculado['mensaje'] and 'se desvinculó' in desvinculado['mensaje']
        assert vinculado['categoria'] == CATEGORIA_AVISO_CUENTAS
        assert nuevo.email not in vinculado['mensaje']

    def test_lo_que_hace_el_propio_dueno_no_se_le_avisa(self, dueno, complejo, crear_usuario, cliente_de, avisos):
        nuevo = crear_usuario('operador.nuevo@talibre.test', 'OPERADOR_COMPLEJO')

        with avisos as entregados:
            cliente_de(dueno).post(f'/api/complejos/{complejo.id}/operadores/', {'email': nuevo.email}, format='json')

        assert _personales(entregados) == []


class TestAvisosALosSuperadmins:
    def test_alta_y_cambio_de_estado_de_un_contrato(self, superadmin, dueno, crear_usuario, cliente_de, avisos):
        otro_superadmin = crear_usuario('segundo.superadmin@talibre.test', 'SUPERADMIN')

        with avisos as entregados:
            alta = cliente_de(superadmin).post('/api/contratos/', {
                'propietario': dueno.id, 'nombre': 'Complejo Nuevo', 'direccion': 'Calle Los Ceibos 900, Goya',
                'latitud': '-29.143000', 'longitud': '-59.265000', 'telefono_contacto': '3777 000150',
            }, format='json')
        (aviso_alta,) = _del_grupo(entregados, otro_superadmin)
        complejo_id = alta.json()['id']
        with avisos as entregados:
            cliente_de(superadmin).patch(
                f'/api/contratos/{complejo_id}/', {'estado_contrato': EstadoContrato.ACTIVO}, format='json',
            )
        (aviso_cambio,) = _del_grupo(entregados, otro_superadmin)

        assert aviso_alta['categoria'] == CATEGORIA_AVISO_SISTEMA and 'Alta de contrato' in aviso_alta['mensaje']
        assert 'Pendiente -> Activo' in aviso_cambio['mensaje']
        assert aviso_alta['complejo_id'] is None and aviso_alta['usuarios_ids'] == [otro_superadmin.id]

    def test_cambio_de_rol_o_suspension_de_una_cuenta(self, superadmin, jugador, crear_usuario, cliente_de, avisos):
        otro_superadmin = crear_usuario('segundo.superadmin@talibre.test', 'SUPERADMIN')

        with avisos as entregados:
            cliente_de(superadmin).patch(
                f'/api/usuarios/{jugador.id}/', {'estado': EstadoUsuario.SUSPENDIDO}, format='json',
            )
        (suspension,) = _del_grupo(entregados, otro_superadmin)
        with avisos as entregados:
            cliente_de(superadmin).patch(
                f'/api/usuarios/{jugador.id}/', {'estado': EstadoUsuario.ACTIVO}, format='json',
            )
        (reactivacion,) = _del_grupo(entregados, otro_superadmin)

        assert suspension['prioridad'] == PRIORIDAD_AVISO_URGENTE and suspension['categoria'] == CATEGORIA_AVISO_CUENTAS
        assert reactivacion['prioridad'] == PRIORIDAD_AVISO_NORMAL
        assert jugador.email not in suspension['mensaje'] and jugador.nombre_completo not in suspension['mensaje']

    def test_editar_solo_el_nombre_no_avisa(self, superadmin, jugador, crear_usuario, cliente_de, avisos):
        crear_usuario('segundo.superadmin@talibre.test', 'SUPERADMIN')

        with avisos as entregados:
            cliente_de(superadmin).patch(f'/api/usuarios/{jugador.id}/', {'nombre_completo': 'Otro Nombre'}, format='json')

        assert entregados == []

    def test_la_baja_de_una_cuenta_indica_si_dejo_senas_retenidas(
        self, superadmin, jugador, cancha, crear_reserva, cliente_de, avisos,
    ):
        crear_reserva(cancha, MARTES, time(18, 0), time(19, 0), estado=EstadoReserva.SENADA)

        with avisos as entregados:
            cliente_de(jugador).delete('/api/perfil/')

        (aviso,) = _del_grupo(entregados, superadmin)
        assert aviso['prioridad'] == PRIORIDAD_AVISO_URGENTE and 'Reservas señadas retenidas: 1' in aviso['mensaje']
        assert jugador.email not in aviso['mensaje']

    def test_la_baja_de_una_cuenta_sin_senas_es_normal(self, superadmin, jugador, cliente_de, avisos):
        with avisos as entregados:
            cliente_de(jugador).delete('/api/perfil/')

        (aviso,) = _del_grupo(entregados, superadmin)
        assert aviso['prioridad'] == PRIORIDAD_AVISO_NORMAL and 'Sin reservas señadas retenidas' in aviso['mensaje']

    def test_el_bloqueo_por_limite_de_intentos_genera_una_alerta_por_ruta_y_ventana(
        self, superadmin, jugador, cliente, avisos,
    ):
        with avisos as entregados:
            for _ in range(8):
                cliente.post('/api/token/', {'email': jugador.email, 'password': 'incorrecta'}, format='json')

        alertas = [aviso for aviso in entregados if aviso['categoria'] == CATEGORIA_AVISO_SISTEMA]
        assert len(alertas) == 1
        assert alertas[0]['usuarios_ids'] == [superadmin.id] and alertas[0]['prioridad'] == PRIORIDAD_AVISO_URGENTE
        assert alertas[0]['clave_unica'].startswith('limite-peticiones-')
        assert jugador.email not in alertas[0]['mensaje'] and 'POST /api/token/' in alertas[0]['mensaje']

    def test_una_falla_al_avisar_no_convierte_el_429_en_un_error_del_servidor(self, jugador, cliente):
        with mock.patch.object(DestinatariosService, 'superadmins', side_effect=DatabaseError('caída')):
            respuestas = [
                cliente.post('/api/token/', {'email': jugador.email, 'password': 'incorrecta'}, format='json')
                for _ in range(7)
            ]

        assert respuestas[-1].status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_sin_superadmins_activos_no_se_emite_nada(self, jugador, cliente, avisos):
        with avisos as entregados:
            for _ in range(8):
                cliente.post('/api/token/', {'email': jugador.email, 'password': 'incorrecta'}, format='json')

        assert entregados == []


class TestUnaCancelacionNoAvisaAUnaCuentaDeBaja:
    def test_un_titular_dado_de_baja_no_recibe_avisos_de_estado(self, jugador, operador, reserva, cliente_de, avisos):
        jugador.estado = EstadoRegistro.BAJA
        jugador.save()

        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.CONFIRMADA)

        assert _del_jugador(entregados, jugador) == []


def test_las_canchas_en_mantenimiento_afectan_a_los_titulares(
    jugador, dueno, cancha, reserva, cliente_de,
    django_capture_on_commit_callbacks,
):
    with mock.patch.object(AvisoComplejoService, 'entregar') as entregar:
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = cliente_de(dueno).patch(
                f'/api/canchas/{cancha.id}/', {'estado': EstadoCancha.EN_MANTENIMIENTO, 'confirmar': True}, format='json',
            )

    assert respuesta.status_code == status.HTTP_200_OK
    avisados = [llamada.args[0]['usuario_id'] for llamada in entregar.call_args_list]
    assert jugador.id in avisados


class TestRegistroDelComplejo:
    """Cada hecho del complejo deja además una entrada de registro, con los ids que lo identifican."""

    def test_un_cambio_de_estado_registra_los_ids_del_turno_el_titular_y_quien_lo_hizo(
        self, jugador, operador, reserva, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.CONFIRMADA)

        registro = next(aviso['registro'] for aviso in entregados if aviso['usuarios_ids'])
        assert registro['ambito'] == 1
        assert registro['mensaje'].startswith(f'{cancha.complejo.nombre}: la reserva id {reserva.id}')
        assert f'Cancha id {cancha.id}' in registro['mensaje']
        assert f'Titular: usuario id {jugador.id}' in registro['mensaje']
        assert f'Hecho por usuario id {operador.id}' in registro['mensaje']

    def test_el_registro_queda_aunque_no_haya_a_quien_avisar(self, dueno, reserva, cliente_de, avisos):
        with avisos as entregados:
            _cambiar_estado(cliente_de, dueno, reserva, EstadoReserva.CONFIRMADA)

        (con_registro,) = [aviso for aviso in entregados if aviso['registro']]
        assert con_registro['usuarios_ids'] is None
        assert f'Hecho por usuario id {dueno.id}' in con_registro['registro']['mensaje']

    def test_la_reserva_web_registra_el_evento_y_el_titular_sin_decir_quien_la_hizo(
        self, jugador, cancha, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(jugador).post('/api/reservas/', {
                'cancha': cancha.id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': '16:00',
            }, format='json')

        aviso = next(aviso for aviso in entregados if aviso['evento'])
        assert aviso['registro']['ambito'] == 1
        assert f'Titular: usuario id {jugador.id}' in aviso['registro']['mensaje']
        assert 'Hecho por' not in aviso['registro']['mensaje']

    def test_lo_comercial_se_registra_con_ambito_comercial_y_el_turno_fijo_con_su_id(
        self, jugador, operador, cancha, crear_turno_fijo, superadmin, cliente_de, avisos,
    ):
        with avisos as entregados:
            cliente_de(superadmin).patch(f'/api/canchas/{cancha.id}/', {'precio_base': '41000'}, format='json')
        (comercial,) = entregados
        turno = crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(20, 0), time(21, 0), desde=MARTES, usuario=jugador,
            nombre_cliente_manual='', telefono_cliente_manual='',
        )
        with avisos as entregados:
            cliente_de(operador).post(
                f'/api/turnos-fijos/{turno.id}/fechas/', {'fecha_turno': MARTES.isoformat()}, format='json',
            )

        operativo = next(aviso['registro'] for aviso in entregados if aviso['usuarios_ids'])
        assert comercial['registro']['ambito'] == 2 and f'Hecho por usuario id {superadmin.id}' in comercial['registro']['mensaje']
        assert operativo['ambito'] == 1 and f'Turno fijo id {turno.id}' in operativo['mensaje']

    def test_los_ids_no_se_pierden_si_el_texto_es_largo(self):
        texto = 'Complejo: ' + 'x' * 400

        resultado = AvisoComplejoService._texto_de_registro(texto, {'cancha': 3, 'titular': 9}, 7)

        assert len(resultado) <= 280
        assert resultado.endswith('(Cancha id 3; Titular: usuario id 9; Hecho por usuario id 7)')

    def test_sin_ids_el_texto_queda_igual(self):
        assert AvisoComplejoService._texto_de_registro('Complejo: algo.', {'reservas': [1, 2]}, None) == 'Complejo: algo.'

    def test_los_avisos_al_jugador_y_al_sistema_no_generan_registro(self, jugador, operador, reserva, cliente_de, avisos):
        with avisos as entregados:
            _cambiar_estado(cliente_de, operador, reserva, EstadoReserva.CONFIRMADA)

        assert _del_jugador(entregados, jugador)[0]['registro'] is None
