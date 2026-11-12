"""Retención de la IP de origen en logs_auditoria: anonimización pasados los meses configurados."""
from datetime import datetime, time, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.models import EstadoRegistro, LogAuditoria, TipoEventoAuditoria
from core.services import AuditoriaService, _sumar_meses

IP = '203.0.113.20'


def _inicio_del_corte(meses):
    corte = _sumar_meses(timezone.localdate(), -meses)
    return datetime.combine(corte, time.min, tzinfo=timezone.get_current_timezone())


@pytest.fixture
def registrar(db):
    def _registrar(fecha, ip=IP, usuario=None, **campos):
        log = LogAuditoria.objects.create(
            tipo_evento=campos.pop('tipo_evento', TipoEventoAuditoria.LOGIN_FALLIDO),
            accion=campos.pop('accion', 'POST /api/token/'),
            ip_origen=ip,
            usuario=usuario,
            **campos,
        )
        # fecha_creacion es auto_now_add: se corrige después de crear para simular un registro antiguo.
        LogAuditoria.objects.filter(pk=log.pk).update(fecha_creacion=fecha)
        return log

    return _registrar


class TestAnonimizacionDeIps:
    def test_anonimiza_solo_los_registros_con_mas_de_la_retencion(self, registrar):
        antiguo = registrar(timezone.now() - timedelta(days=13 * 31))
        reciente = registrar(timezone.now() - timedelta(days=6 * 30))

        cantidad = AuditoriaService.anonimizar_ips_vencidas()

        antiguo.refresh_from_db()
        reciente.refresh_from_db()
        assert cantidad == 1
        assert antiguo.ip_origen is None
        assert reciente.ip_origen == IP

    def test_el_limite_es_el_inicio_del_dia_de_hace_doce_meses(self, registrar):
        corte = _inicio_del_corte(12)
        justo_antes = registrar(corte - timedelta(seconds=1))
        justo_despues = registrar(corte)

        AuditoriaService.anonimizar_ips_vencidas()

        justo_antes.refresh_from_db()
        justo_despues.refresh_from_db()
        assert justo_antes.ip_origen is None
        assert justo_despues.ip_origen == IP

    def test_conserva_el_evento_la_fecha_y_el_usuario(self, registrar, crear_usuario):
        titular = crear_usuario('titular@talibre.test')
        fecha = timezone.now() - timedelta(days=500)
        log = registrar(fecha, usuario=titular, accion='POST /api/token/', detalle='Intento fallido')

        AuditoriaService.anonimizar_ips_vencidas()

        log.refresh_from_db()
        assert log.ip_origen is None
        assert log.tipo_evento == TipoEventoAuditoria.LOGIN_FALLIDO
        assert log.accion == 'POST /api/token/'
        assert log.detalle == 'Intento fallido'
        assert log.usuario_id == titular.pk
        assert log.fecha_creacion == fecha
        assert log.estado == EstadoRegistro.ACTIVO

    def test_actualiza_la_fecha_de_modificacion(self, registrar):
        log = registrar(timezone.now() - timedelta(days=500))
        antes = LogAuditoria.objects.get(pk=log.pk).fecha_modificacion

        AuditoriaService.anonimizar_ips_vencidas()

        log.refresh_from_db()
        assert log.fecha_modificacion > antes

    def test_no_borra_registros(self, registrar):
        for dias in (30, 400, 800):
            registrar(timezone.now() - timedelta(days=dias))

        AuditoriaService.anonimizar_ips_vencidas()

        assert LogAuditoria.objects.count() == 3

    def test_es_idempotente(self, registrar):
        registrar(timezone.now() - timedelta(days=500))
        registrar(timezone.now() - timedelta(days=900))

        assert AuditoriaService.anonimizar_ips_vencidas() == 2
        assert AuditoriaService.anonimizar_ips_vencidas() == 0

    def test_ignora_los_registros_que_no_tienen_ip(self, registrar):
        registrar(timezone.now() - timedelta(days=500), ip=None)

        assert AuditoriaService.anonimizar_ips_vencidas() == 0

    def test_alcanza_tambien_a_los_registros_dados_de_baja(self, registrar):
        log = registrar(timezone.now() - timedelta(days=500), estado=EstadoRegistro.BAJA)

        AuditoriaService.anonimizar_ips_vencidas()

        log.refresh_from_db()
        assert log.ip_origen is None
        assert log.estado == EstadoRegistro.BAJA

    def test_respeta_el_plazo_configurado(self, registrar, settings):
        settings.AUDITORIA_RETENCION_MESES = 6
        entre_seis_y_doce = registrar(timezone.now() - timedelta(days=9 * 30))

        AuditoriaService.anonimizar_ips_vencidas()

        entre_seis_y_doce.refresh_from_db()
        assert entre_seis_y_doce.ip_origen is None

    def test_con_el_plazo_por_defecto_un_registro_de_nueve_meses_conserva_la_ip(self, registrar):
        nueve_meses = registrar(timezone.now() - timedelta(days=9 * 30))

        AuditoriaService.anonimizar_ips_vencidas()

        nueve_meses.refresh_from_db()
        assert nueve_meses.ip_origen == IP


class TestComando:
    def test_informa_la_cantidad_anonimizada(self, registrar):
        registrar(timezone.now() - timedelta(days=500))
        salida = StringIO()

        call_command('anonimizar_ips_auditoria', stdout=salida)

        assert 'Registros de auditoría con la IP anonimizada: 1' in salida.getvalue()
        assert 'retención: 12 meses' in salida.getvalue()

    def test_una_segunda_ejecucion_no_cambia_nada(self, registrar):
        registrar(timezone.now() - timedelta(days=500))
        call_command('anonimizar_ips_auditoria', stdout=StringIO())
        salida = StringIO()

        call_command('anonimizar_ips_auditoria', stdout=salida)

        assert 'anonimizada: 0' in salida.getvalue()
