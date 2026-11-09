import logging
from datetime import time, timedelta
from io import StringIO
from unittest import mock

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from rest_framework import status

from conftest import HOY_CONGELADO, PASSWORD_PRUEBA
from core.models import (
    DiaSemana,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    EstadoTurnoFijo,
    EstadoUsuario,
    LogAuditoria,
    RolPermiso,
    TipoEventoAuditoria,
)
from core.services import (
    PRIORIDAD_AVISO_NORMAL,
    PRIORIDAD_AVISO_URGENTE,
    AvisoComplejoService,
    BajaDeCuentaService,
    DifusionGrillaService,
)

URL = '/api/perfil/'


class TestConsulta:
    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno', 'superadmin'])
    def test_todos_los_roles_ven_su_perfil(self, request, cliente_de, fixture_usuario):
        usuario = request.getfixturevalue(fixture_usuario)

        respuesta = cliente_de(usuario).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['email'] == usuario.email
        assert respuesta.json()['rol'] == usuario.rol.nombre

    def test_no_expone_la_contrasena(self, jugador, cliente_de):
        cuerpo = cliente_de(jugador).get(URL).json()

        assert 'password' not in cuerpo
        assert set(cuerpo) == {
            'id', 'email', 'nombre_completo', 'telefono', 'rol',
            'complejo_operado', 'estado', 'estado_nombre', 'version_politica_aceptada',
            'fecha_aceptacion_politica', 'debe_aceptar_politica', 'fecha_creacion',
        }

    def test_operador_ve_su_complejo(self, operador, complejo, cliente_de):
        assert cliente_de(operador).get(URL).json()['complejo_operado'] == complejo.id

    def test_sin_permiso_ver_perfil_propio_responde_403(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='ver_perfil_propio').desactivar()

        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN


class TestEdicion:
    def test_edita_nombre_y_telefono(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(
            URL, {'nombre_completo': 'Jugador Editado', 'telefono': '+54 3777 001234'}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Jugador Editado'
        assert jugador.telefono == '+54 3777 001234'

    def test_edicion_parcial_conserva_lo_demas(self, jugador, cliente_de):
        cliente_de(jugador).patch(URL, {'telefono': '3777 009999'}, format='json')

        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Jugador Prueba'
        assert jugador.telefono == '3777 009999'

    def test_no_permite_cambiar_email_rol_ni_estado(self, jugador, cliente_de):
        cliente_de(jugador).patch(
            URL,
            {'nombre_completo': 'Otro Nombre', 'email': 'nuevo@talibre.test', 'rol': 1, 'estado': 2},
            format='json',
        )

        jugador.refresh_from_db()
        assert jugador.email == 'jugador@talibre.test'
        assert jugador.rol.nombre == 'JUGADOR'
        assert jugador.estado == EstadoRegistro.ACTIVO

    def test_sanitiza_el_nombre(self, jugador, cliente_de):
        cliente_de(jugador).patch(URL, {'nombre_completo': '<img src=x onerror=alert(1)>Ana & Cía'}, format='json')

        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Ana & Cía'

    @pytest.mark.parametrize('datos, campo', [
        ({'nombre_completo': '<b></b>'}, 'nombre_completo'),
        ({'telefono': 'sin número'}, 'telefono'),
        ({'nombre_completo': 'x' * 121}, 'nombre_completo'),
    ])
    def test_rechaza_datos_invalidos(self, jugador, cliente_de, datos, campo):
        respuesta = cliente_de(jugador).patch(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_body_vacio_responde_400(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(URL, {}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['error'] is True

    def test_sin_permiso_editar_responde_403_y_audita(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='editar_perfil_propio').desactivar()
        cliente = cliente_de(jugador)

        respuesta = cliente.patch(URL, {'telefono': '3777 000000'}, format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert respuesta.json() == {'error': True, 'detail': 'No tenés permiso para realizar esta acción.'}
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO)
        assert log.usuario == jugador
        assert log.accion == 'PATCH /api/perfil/'
        assert cliente.get(URL).status_code == status.HTTP_200_OK


class TestBajaLogica:
    def test_baja_logica_con_estado_cero(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).delete(URL)

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        jugador.refresh_from_db()
        assert jugador.estado == EstadoRegistro.BAJA
        assert type(jugador).objects.filter(pk=jugador.pk).exists()

    def test_audita_la_baja(self, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO)
        assert log.usuario == jugador

    def test_el_access_deja_de_servir(self, jugador, cliente_de):
        cliente = cliente_de(jugador)
        cliente.delete(URL)

        respuesta = cliente.get(URL)

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json()['detail'] == 'La cuenta no está activa.'

    def test_revoca_las_sesiones_abiertas_y_borra_la_cookie(self, cliente, jugador, cliente_de):
        cliente.post('/api/token/', {'email': jugador.email, 'password': PASSWORD_PRUEBA}, format='json')
        refresh = cliente.cookies['refresh'].value

        respuesta = cliente_de(jugador).delete(URL)

        assert respuesta.cookies['refresh'].value == ''
        cliente.cookies['refresh'] = refresh
        assert cliente.post('/api/token/refresh/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_puede_volver_a_iniciar_sesion(self, cliente, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        respuesta = cliente.post('/api/token/', {'email': jugador.email, 'password': PASSWORD_PRUEBA}, format='json')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED

    def test_el_unico_superadmin_activo_no_puede_darse_de_baja(self, superadmin, cliente_de):
        respuesta = cliente_de(superadmin).delete(URL)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'única cuenta de superadministrador activa' in respuesta.json()['detail']
        superadmin.refresh_from_db()
        assert superadmin.estado == EstadoRegistro.ACTIVO
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO).exists()

    def test_un_superadmin_suspendido_no_cuenta_como_reemplazo(self, superadmin, crear_usuario, cliente_de):
        suspendido = crear_usuario('suspendido@talibre.test', 'SUPERADMIN')
        suspendido.estado = EstadoUsuario.SUSPENDIDO
        suspendido.save(update_fields=['estado'])

        assert cliente_de(superadmin).delete(URL).status_code == status.HTTP_400_BAD_REQUEST

    def test_con_otro_superadmin_activo_la_baja_procede(self, superadmin, crear_usuario, cliente_de):
        otro = crear_usuario('otro.superadmin@talibre.test', 'SUPERADMIN')

        assert cliente_de(superadmin).delete(URL).status_code == status.HTTP_204_NO_CONTENT
        superadmin.refresh_from_db()
        assert superadmin.estado == EstadoRegistro.BAJA
        assert cliente_de(otro).delete(URL).status_code == status.HTTP_400_BAD_REQUEST

    def test_la_auditoria_de_la_baja_no_guarda_el_email(self, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        assert jugador.email not in LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO).detalle

    def test_sin_permiso_desactivar_responde_403(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='desactivar_perfil_propio').desactivar()

        assert cliente_de(jugador).delete(URL).status_code == status.HTTP_403_FORBIDDEN
        jugador.refresh_from_db()
        assert jugador.estado == EstadoRegistro.ACTIVO


class TestAceptacionDePolitica:
    def test_una_cuenta_sin_constancia_debe_aceptar_la_politica(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).json()['debe_aceptar_politica'] is True

    def test_aceptar_la_version_vigente_deja_constancia_y_auditoria(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(URL, {'acepta_politica_privacidad': True}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['debe_aceptar_politica'] is False
        jugador.refresh_from_db()
        assert jugador.version_politica_aceptada == settings.POLITICA_PRIVACIDAD_VERSION
        assert jugador.fecha_aceptacion_politica is not None
        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ACEPTACION_POLITICA)
        assert log.usuario == jugador
        assert log.ip_origen == '127.0.0.1'

    def test_no_admite_aceptacion_falsa(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).patch(URL, {'acepta_politica_privacidad': False}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'acepta_politica_privacidad' in respuesta.json()['detail']

    def test_editar_datos_no_registra_aceptacion(self, jugador, cliente_de):
        cliente_de(jugador).patch(URL, {'telefono': '3777 001111'}, format='json')

        jugador.refresh_from_db()
        assert jugador.fecha_aceptacion_politica is None
        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACEPTACION_POLITICA).exists()

    def test_una_version_nueva_pide_aceptarla_otra_vez(self, jugador, cliente_de):
        cliente = cliente_de(jugador)
        cliente.patch(URL, {'acepta_politica_privacidad': True}, format='json')

        with override_settings(POLITICA_PRIVACIDAD_VERSION='2.0'):
            assert cliente.get(URL).json()['debe_aceptar_politica'] is True

    def test_el_admin_no_permite_editar_la_constancia(self):
        from django.contrib import admin

        from core.models import Usuario

        campos = admin.site._registry[Usuario].readonly_fields
        assert {'version_politica_aceptada', 'fecha_aceptacion_politica'}.issubset(campos)


class TestSupresionDeDatos:
    def test_la_baja_anonimiza_los_datos_personales(self, jugador, cliente_de):
        jugador.telefono = '3777 000206'
        jugador.save(update_fields=['telefono'])

        cliente_de(jugador).delete(URL)

        jugador.refresh_from_db()
        assert jugador.nombre_completo == 'Usuario dado de baja'
        assert jugador.email == f'baja-{jugador.pk}@talibre.invalid'
        assert jugador.telefono == ''
        assert not jugador.has_usable_password()
        assert jugador.estado == EstadoRegistro.BAJA

    def test_el_email_original_queda_libre_para_registrarse_de_nuevo(self, cliente, jugador, cliente_de):
        cliente_de(jugador).delete(URL)

        respuesta = cliente.post('/api/registro/', {
            'nombre_completo': 'Jugador Vuelve',
            'email': 'jugador@talibre.test',
            'password': 'Pelota&Arco#2026',
            'acepta_politica_privacidad': True,
        }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_el_operador_se_desvincula_de_su_complejo(self, operador, cliente_de):
        cliente_de(operador).delete(URL)

        operador.refresh_from_db()
        assert operador.complejo_operado is None

    def test_la_auditoria_conserva_la_referencia_sin_datos_personales(self, jugador, cliente_de):
        email = jugador.email
        cliente_de(jugador).delete(URL)

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO)
        assert log.usuario_id == jugador.pk
        assert email not in log.detalle
        assert 'anonimizados' in log.detalle

    def test_dueno_con_contrato_vigente_no_puede_darse_de_baja(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).delete(URL)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'contrato vigente' in respuesta.json()['detail']
        dueno.refresh_from_db()
        assert dueno.estado == EstadoRegistro.ACTIVO
        assert dueno.email == 'dueno@talibre.test'

    @pytest.mark.parametrize('dar_de_baja', ['contrato', 'complejo'])
    def test_dueno_sin_contratos_vigentes_puede_darse_de_baja(self, dueno, complejo, cliente_de, dar_de_baja):
        if dar_de_baja == 'contrato':
            complejo.estado_contrato = EstadoContrato.BAJA
            complejo.save(update_fields=['estado_contrato'])
        else:
            complejo.desactivar()

        assert cliente_de(dueno).delete(URL).status_code == status.HTTP_204_NO_CONTENT

    def test_si_la_baja_se_rechaza_no_se_anonimiza_nada(self, superadmin, cliente_de):
        cliente_de(superadmin).delete(URL)

        superadmin.refresh_from_db()
        assert superadmin.email == 'superadmin@talibre.test'
        assert superadmin.has_usable_password()


URL_BAJA = '/api/perfil/baja/'
MARTES = HOY_CONGELADO + timedelta(days=1)


@pytest.fixture
def con_reservas(reloj, jugador, complejo, crear_cancha, crear_horario, crear_reserva, crear_turno_fijo):
    """
    El reloj marca el lunes 16/11/2026 a las 10:00. La jugadora tiene, para el martes, una reserva pendiente,
    una confirmada y una señada; además, una completada de la semana pasada, una cancelada y un turno fijo.
    """
    jugador.nombre_completo = 'Lucía Benítez'
    jugador.telefono = '3777 000615'
    jugador.save()
    cancha = crear_cancha(complejo, 'Cancha 1')
    crear_horario(cancha, DiaSemana.MARTES, time(14, 0), time(23, 0))
    return {
        'cancha': cancha,
        'pendiente': crear_reserva(cancha, MARTES, time(14, 0), time(15, 0), estado=EstadoReserva.PENDIENTE),
        'confirmada': crear_reserva(cancha, MARTES, time(15, 0), time(16, 0), estado=EstadoReserva.CONFIRMADA),
        'senada': crear_reserva(cancha, MARTES, time(20, 0), time(21, 0), estado=EstadoReserva.SENADA),
        'pasada': crear_reserva(cancha, MARTES - timedelta(days=7), time(20, 0), time(21, 0),
                                estado=EstadoReserva.COMPLETADA),
        'cancelada': crear_reserva(cancha, MARTES, time(16, 0), time(17, 0), estado=EstadoReserva.CANCELADA_JUGADOR),
        'turno_fijo': crear_turno_fijo(
            cancha, DiaSemana.MARTES, time(21, 0), time(22, 0), desde=MARTES, usuario=jugador,
            nombre_cliente_manual='', telefono_cliente_manual='',
        ),
    }


def _baja(cliente_de, usuario, captura=None):
    if captura is None:
        return cliente_de(usuario).delete(URL)
    with captura(execute=True):
        return cliente_de(usuario).delete(URL)


class TestVistaPreviaDeLaBaja:
    def test_informa_que_se_cancela_y_que_se_conserva(self, jugador, cliente_de, con_reservas):
        respuesta = cliente_de(jugador).get(URL_BAJA)

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert cuerpo['reservas_a_cancelar'] == 2
        assert cuerpo['reservas_senadas_conservadas'] == 1
        assert cuerpo['turnos_fijos_a_dar_de_baja'] == 1
        assert cuerpo['impedimento'] is None
        (aviso,) = cuerpo['avisos']
        assert aviso.startswith('1 reserva señada o pagada no se cancela')
        assert 'nombre y tu teléfono' in aviso and '30 días' in aviso

    def test_no_modifica_nada(self, jugador, cliente_de, con_reservas):
        cliente_de(jugador).get(URL_BAJA)

        con_reservas['pendiente'].refresh_from_db()
        jugador.refresh_from_db()
        assert con_reservas['pendiente'].estado == EstadoReserva.PENDIENTE
        assert jugador.estado == EstadoRegistro.ACTIVO

    def test_sin_reservas_no_hay_avisos(self, reloj, jugador, cliente_de):
        assert cliente_de(jugador).get(URL_BAJA).json() == {
            'reservas_a_cancelar': 0, 'reservas_senadas_conservadas': 0, 'turnos_fijos_a_dar_de_baja': 0,
            'avisos': [], 'impedimento': None,
        }

    def test_un_turno_ya_iniciado_no_se_cuenta(self, reloj, jugador, cliente_de, con_reservas):
        reloj.return_value = reloj.return_value.replace(day=17, hour=15, minute=30)

        cuerpo = cliente_de(jugador).get(URL_BAJA).json()

        assert cuerpo['reservas_a_cancelar'] == 0
        assert cuerpo['reservas_senadas_conservadas'] == 1

    def test_anticipa_el_rechazo_del_ultimo_superadmin(self, superadmin, cliente_de):
        assert 'única cuenta de superadministrador' in cliente_de(superadmin).get(URL_BAJA).json()['impedimento']

    def test_anticipa_el_rechazo_de_un_dueno_con_contratos(self, dueno, complejo, cliente_de):
        assert 'contrato vigente' in cliente_de(dueno).get(URL_BAJA).json()['impedimento']

    def test_sin_sesion_responde_401(self, cliente):
        assert cliente.get(URL_BAJA).status_code == status.HTTP_401_UNAUTHORIZED

    def test_sin_el_permiso_de_baja_responde_403(self, jugador, cliente_de):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='desactivar_perfil_propio').desactivar()

        assert cliente_de(jugador).get(URL_BAJA).status_code == status.HTTP_403_FORBIDDEN


class TestBajaConReservas:
    def test_cancela_las_pendientes_y_confirmadas_futuras(self, jugador, cliente_de, con_reservas):
        assert _baja(cliente_de, jugador).status_code == status.HTTP_204_NO_CONTENT

        for clave in ('pendiente', 'confirmada'):
            con_reservas[clave].refresh_from_db()
            assert con_reservas[clave].estado == EstadoReserva.CANCELADA_JUGADOR
            assert con_reservas[clave].nombre_cliente_manual == ''

    def test_conserva_las_senadas_con_una_copia_del_contacto(self, jugador, cliente_de, con_reservas):
        _baja(cliente_de, jugador)

        senada = con_reservas['senada']
        senada.refresh_from_db()
        jugador.refresh_from_db()
        assert senada.estado == EstadoReserva.SENADA
        assert (senada.nombre_cliente_manual, senada.telefono_cliente_manual) == ('Lucía Benítez', '3777 000615')
        assert jugador.nombre_completo == 'Usuario dado de baja' and jugador.telefono == ''

    def test_no_toca_el_historial_ni_lo_ya_cancelado(self, jugador, cliente_de, con_reservas):
        _baja(cliente_de, jugador)

        for clave, estado in (('pasada', EstadoReserva.COMPLETADA), ('cancelada', EstadoReserva.CANCELADA_JUGADOR)):
            con_reservas[clave].refresh_from_db()
            assert con_reservas[clave].estado == estado
            assert con_reservas[clave].nombre_cliente_manual == ''

    def test_un_turno_en_curso_no_se_cancela(self, reloj, jugador, cliente_de, con_reservas):
        reloj.return_value = reloj.return_value.replace(day=17, hour=14, minute=30)

        _baja(cliente_de, jugador)

        con_reservas['pendiente'].refresh_from_db()
        con_reservas['confirmada'].refresh_from_db()
        assert con_reservas['pendiente'].estado == EstadoReserva.PENDIENTE
        assert con_reservas['confirmada'].estado == EstadoReserva.CANCELADA_JUGADOR

    def test_da_de_baja_los_turnos_fijos_vigentes_y_pausados(self, jugador, crear_turno_fijo, cliente_de, con_reservas):
        pausado = crear_turno_fijo(
            con_reservas['cancha'], DiaSemana.JUEVES, time(21, 0), time(22, 0), desde=MARTES, usuario=jugador,
            nombre_cliente_manual='', estado=EstadoTurnoFijo.PAUSADO,
        )

        _baja(cliente_de, jugador)

        for turno in (con_reservas['turno_fijo'], pausado):
            turno.refresh_from_db()
            assert turno.estado == EstadoTurnoFijo.BAJA

    def test_no_toca_las_reservas_de_otros(self, jugador, crear_usuario, crear_reserva, cliente_de, con_reservas):
        otra = crear_usuario('otra.jugadora@talibre.test')
        ajena = crear_reserva(con_reservas['cancha'], MARTES, time(17, 0), time(18, 0), usuario=otra, creado_por=otra)

        _baja(cliente_de, jugador)

        ajena.refresh_from_db()
        assert ajena.estado == EstadoReserva.CONFIRMADA

    def test_los_horarios_liberados_se_pueden_volver_a_reservar(self, jugador, crear_usuario, cliente_de, con_reservas):
        _baja(cliente_de, jugador)
        api = cliente_de(crear_usuario('otra.jugadora@talibre.test'))

        def reservar(hora):
            return api.post('/api/reservas/', {
                'cancha': con_reservas['cancha'].id, 'fecha_turno': MARTES.isoformat(), 'hora_inicio': hora,
            }, format='json').status_code

        assert reservar('14:00') == status.HTTP_201_CREATED
        assert reservar('21:00') == status.HTTP_201_CREATED
        assert reservar('20:00') == status.HTTP_409_CONFLICT

    def test_las_grillas_se_actualizan_despues_del_commit(
        self, jugador, complejo, cliente_de, con_reservas, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            _baja(cliente_de, jugador, django_capture_on_commit_callbacks)

        eventos = {(llamada.args[1]['hora_inicio'], llamada.args[1]['fecha_hasta']) for llamada in publicar.call_args_list}
        assert eventos == {('14:00:00', MARTES.isoformat()), ('15:00:00', MARTES.isoformat()), ('21:00:00', None)}
        assert {llamada.args[0] for llamada in publicar.call_args_list} == {complejo.id}

    def test_avisa_al_complejo_sin_datos_personales(
        self, jugador, complejo, cliente_de, con_reservas, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(AvisoComplejoService, 'entregar') as entregar:
            _baja(cliente_de, jugador, django_capture_on_commit_callbacks)

        avisos = {llamada.args[0]['prioridad']: llamada.args[0] for llamada in entregar.call_args_list}
        urgente, normal = avisos[PRIORIDAD_AVISO_URGENTE], avisos[PRIORIDAD_AVISO_NORMAL]
        assert urgente['complejo_id'] == complejo.id
        assert urgente['referencias'] == {'reservas': [con_reservas['senada'].id]}
        assert normal['referencias'] == {'turnos_fijos': [con_reservas['turno_fijo'].id]}
        for aviso in (urgente, normal):
            assert 'Lucía' not in aviso['mensaje'] and '000615' not in aviso['mensaje']

    def test_sin_mensajeria_conectada_el_aviso_queda_en_el_log(
        self, jugador, cliente_de, con_reservas, caplog, django_capture_on_commit_callbacks,
    ):
        logger = logging.getLogger('core')
        logger.addHandler(caplog.handler)
        try:
            respuesta = _baja(cliente_de, jugador, django_capture_on_commit_callbacks)
        finally:
            logger.removeHandler(caplog.handler)

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        assert 'sin entregar' in caplog.text and 'prioridad 2' in caplog.text
        assert 'Lucía' not in caplog.text

    def test_una_falla_al_avisar_no_revierte_la_baja(
        self, jugador, cliente_de, con_reservas, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(AvisoComplejoService, 'entregar', side_effect=ConnectionError('Node caído')):
            respuesta = _baja(cliente_de, jugador, django_capture_on_commit_callbacks)

        jugador.refresh_from_db()
        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        assert jugador.estado == EstadoRegistro.BAJA

    def test_audita_el_resumen_y_cada_cancelacion_sin_datos_personales(self, jugador, cliente_de, con_reservas):
        _baja(cliente_de, jugador)

        baja = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_USUARIO)
        cancelaciones = list(LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.RESERVA_CANCELADA))
        assert 'Reservas canceladas: 2. Reservas señadas conservadas: 1. Turnos fijos dados de baja: 1.' in baja.detalle
        assert len(cancelaciones) == 2
        assert all('-> Cancelada por el jugador.' in log.detalle for log in cancelaciones)
        for log in (baja, *cancelaciones):
            assert 'Lucía' not in log.detalle and '000615' not in log.detalle

    def test_si_la_baja_se_rechaza_las_reservas_quedan_como_estaban(
        self, superadmin, crear_reserva, cliente_de, con_reservas,
    ):
        reserva = crear_reserva(con_reservas['cancha'], MARTES, time(18, 0), time(19, 0),
                                usuario=superadmin, creado_por=superadmin)

        assert _baja(cliente_de, superadmin).status_code == status.HTTP_400_BAD_REQUEST
        reserva.refresh_from_db()
        assert reserva.estado == EstadoReserva.CONFIRMADA


class TestContactoConservadoDeLaSenada:
    @pytest.fixture
    def senada_de_baja(self, jugador, cliente_de, con_reservas):
        _baja(cliente_de, jugador)
        senada = con_reservas['senada']
        senada.refresh_from_db()
        return senada

    def test_la_agenda_muestra_la_copia_y_nunca_la_cuenta_anonimizada(
        self, dueno, cliente_de, con_reservas, senada_de_baja,
    ):
        agenda = {r['id']: r for r in cliente_de(dueno).get('/api/agenda/').json()['results']}

        assert agenda[senada_de_baja.id]['cliente'] == {
            'nombre': 'Lucía Benítez', 'telefono': '3777 000615', 'email': None,
        }
        assert agenda[con_reservas['pendiente'].id]['cliente'] == {
            'nombre': 'Titular dado de baja', 'telefono': '', 'email': None,
        }
        assert 'talibre.invalid' not in str(agenda)

    @pytest.mark.parametrize('estado', [EstadoReserva.AUSENTE, EstadoReserva.COMPLETADA])
    def test_se_borra_al_cerrar_el_turno(self, reloj, dueno, cliente_de, senada_de_baja, estado):
        reloj.return_value = reloj.return_value.replace(day=17, hour=21, minute=5)

        respuesta = cliente_de(dueno).patch(f'/api/agenda/{senada_de_baja.id}/', {'estado': estado}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        senada_de_baja.refresh_from_db()
        assert (senada_de_baja.nombre_cliente_manual, senada_de_baja.telefono_cliente_manual) == ('', '')
        assert respuesta.json()['cliente']['nombre'] == 'Titular dado de baja'

    def test_un_turno_en_curso_sin_copia_se_cierra_sin_tocar_nada_mas(self, reloj, jugador, dueno, cliente_de, con_reservas):
        reloj.return_value = reloj.return_value.replace(day=17, hour=14, minute=30)
        _baja(cliente_de, jugador)
        reloj.return_value = reloj.return_value.replace(hour=15, minute=5)
        en_curso = con_reservas['pendiente']

        respuesta = cliente_de(dueno).patch(f'/api/agenda/{en_curso.id}/', {'estado': EstadoReserva.AUSENTE}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['cliente'] == {'nombre': 'Titular dado de baja', 'telefono': '', 'email': None}

    def test_se_borra_al_cancelarla_desde_el_complejo(self, dueno, cliente_de, senada_de_baja):
        cliente_de(dueno).post(f'/api/agenda/{senada_de_baja.id}/cancelar/')

        senada_de_baja.refresh_from_db()
        assert (senada_de_baja.nombre_cliente_manual, senada_de_baja.telefono_cliente_manual) == ('', '')

    def test_editar_las_observaciones_no_la_borra(self, dueno, cliente_de, senada_de_baja):
        cliente_de(dueno).patch(f'/api/agenda/{senada_de_baja.id}/', {'observaciones': 'Llamar'}, format='json')

        senada_de_baja.refresh_from_db()
        assert senada_de_baja.nombre_cliente_manual == 'Lucía Benítez'

    def test_la_depuracion_diaria_la_borra_pasados_30_dias_del_turno(
        self, reloj, crear_reserva, con_reservas, senada_de_baja,
    ):
        titular = senada_de_baja.usuario
        reciente = crear_reserva(
            con_reservas['cancha'], MARTES + timedelta(days=7), time(20, 0), time(21, 0), estado=EstadoReserva.SENADA,
            usuario=titular, creado_por=titular, nombre_cliente_manual='Lucía Benítez',
            telefono_cliente_manual='3777 000615',
        )
        salida = StringIO()

        # El turno fue el martes 17/11: el 17/12 se cumplen 30 días y el 18/12 ya se depura.
        reloj.return_value += timedelta(days=31)
        call_command('purgar_contactos_de_bajas', stdout=StringIO())
        senada_de_baja.refresh_from_db()
        assert senada_de_baja.nombre_cliente_manual == 'Lucía Benítez'

        reloj.return_value += timedelta(days=1)
        call_command('purgar_contactos_de_bajas', stdout=salida)

        senada_de_baja.refresh_from_db()
        reciente.refresh_from_db()
        assert (senada_de_baja.nombre_cliente_manual, senada_de_baja.telefono_cliente_manual) == ('', '')
        assert senada_de_baja.estado == EstadoReserva.SENADA
        assert reciente.nombre_cliente_manual == 'Lucía Benítez'
        assert 'Reservas con datos de contacto depurados: 1' in salida.getvalue()

    def test_la_depuracion_no_toca_clientes_manuales(self, reloj, crear_reserva, con_reservas):
        manual = crear_reserva(con_reservas['cancha'], MARTES - timedelta(days=60), time(20, 0), time(21, 0),
                               usuario=None, nombre_cliente_manual='Rosendo Aquino')

        assert BajaDeCuentaService.purgar_contactos_vencidos() == 0
        manual.refresh_from_db()
        assert manual.nombre_cliente_manual == 'Rosendo Aquino'
