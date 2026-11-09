from datetime import date, datetime, time
from decimal import Decimal
from itertools import count
from zoneinfo import ZoneInfo

import pytest
from rest_framework import status

from core.models import (
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    EstadoReserva,
    LogAuditoria,
    Reserva,
    RolPermiso,
    TipoEventoAuditoria,
    TipoOcupacion,
)
from core.services import MAXIMO_DIAS_REPORTE, ReporteService

URL = '/api/reportes/dashboard/'
MENSAJE_CANCHA_AJENA = 'La cancha no pertenece al complejo.'
HORA_LOCAL = ZoneInfo('America/Argentina/Buenos_Aires')
MITAD_DE_MES = date(2026, 11, 16)
SIN_RECAUDACION = {'total': '0.00', 'senada': '0.00'}


def _parametros(complejo, /, **cambios):
    parametros = {'complejo': complejo.id, 'fecha_desde': '2026-11-01', 'fecha_hasta': '2026-11-30'}
    parametros.update(cambios)
    return {clave: valor for clave, valor in parametros.items() if valor is not None}


@pytest.fixture
def cancha(complejo, crear_cancha):
    return crear_cancha(complejo, 'Cancha Propia')


@pytest.fixture
def cancha_ajena(complejo_ajeno, crear_cancha):
    return crear_cancha(complejo_ajeno, 'Cancha Ajena')


@pytest.fixture
def deporte(cancha):
    return cancha.deporte


@pytest.mark.django_db
class TestAccesoAlDashboard:
    def test_sin_token_responde_401(self, cliente, complejo):
        assert cliente.get(URL, _parametros(complejo)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_jugador_recibe_403(self, jugador, complejo, cliente_de):
        assert cliente_de(jugador).get(URL, _parametros(complejo)).status_code == status.HTTP_403_FORBIDDEN

    def test_operador_recibe_403_porque_los_reportes_son_comerciales(self, operador, complejo, cliente_de):
        assert cliente_de(operador).get(URL, _parametros(complejo)).status_code == status.HTTP_403_FORBIDDEN

    def test_el_403_queda_auditado(self, operador, complejo, cliente_de):
        cliente_de(operador).get(URL, _parametros(complejo))

        assert LogAuditoria.objects.filter(
            usuario=operador, tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO,
        ).exists()

    def test_dueno_sin_ver_reportes_recibe_403(self, dueno, complejo, cliente_de):
        RolPermiso.objects.get(rol__nombre='DUENO_COMPLEJO', permiso__codigo='ver_reportes').desactivar()

        assert cliente_de(dueno).get(URL, _parametros(complejo)).status_code == status.HTTP_403_FORBIDDEN

    def test_dueno_consulta_su_complejo(self, dueno, complejo, cliente_de):
        assert cliente_de(dueno).get(URL, _parametros(complejo)).status_code == status.HTTP_200_OK

    def test_complejo_ajeno_responde_404(self, dueno, complejo_ajeno, cliente_de):
        assert cliente_de(dueno).get(URL, _parametros(complejo_ajeno)).status_code == status.HTTP_404_NOT_FOUND

    def test_complejo_inexistente_responde_404(self, superadmin, complejo, cliente_de):
        parametros = _parametros(complejo, complejo=complejo.id + 999)

        assert cliente_de(superadmin).get(URL, parametros).status_code == status.HTTP_404_NOT_FOUND

    def test_complejo_dado_de_baja_responde_404(self, superadmin, complejo, cliente_de):
        complejo.desactivar()

        assert cliente_de(superadmin).get(URL, _parametros(complejo)).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize('estado_contrato', [EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO])
    def test_el_historial_se_consulta_aunque_el_contrato_no_este_activo(
        self, dueno, complejo, cliente_de, estado_contrato,
    ):
        complejo.estado_contrato = estado_contrato
        complejo.save(update_fields=['estado_contrato'])

        assert cliente_de(dueno).get(URL, _parametros(complejo)).status_code == status.HTTP_200_OK

    def test_superadmin_consulta_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        assert cliente_de(superadmin).get(URL, _parametros(complejo_ajeno)).status_code == status.HTTP_200_OK

    def test_superadmin_hereda_ver_reportes_del_dueno(self, superadmin, complejo, cliente_de):
        RolPermiso.objects.filter(rol__nombre='SUPERADMIN', permiso__codigo='ver_reportes').update(
            estado=EstadoRegistro.BAJA,
        )

        assert cliente_de(superadmin).get(URL, _parametros(complejo)).status_code == status.HTTP_200_OK

    def test_solo_admite_get(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _parametros(complejo), format='json')

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestValidacionDeFiltros:
    def _detalle(self, respuesta):
        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        cuerpo = respuesta.json()
        assert cuerpo['error'] is True
        return cuerpo['detail']

    @pytest.mark.parametrize('faltante', ['complejo', 'fecha_desde', 'fecha_hasta'])
    def test_los_parametros_base_son_obligatorios(self, dueno, complejo, cliente_de, faltante):
        detalle = self._detalle(cliente_de(dueno).get(URL, _parametros(complejo, **{faltante: None})))

        assert faltante in detalle

    @pytest.mark.parametrize('campo,valor', [
        ('complejo', 'abc'),
        ('complejo', '0'),
        ('fecha_desde', '01/11/2026'),
        ('fecha_hasta', '2026-02-30'),
        ('cancha_id', 'uno'),
        ('deporte_id', '-3'),
    ])
    def test_formatos_invalidos(self, dueno, complejo, cliente_de, campo, valor):
        detalle = self._detalle(cliente_de(dueno).get(URL, _parametros(complejo, **{campo: valor})))

        assert campo in detalle

    def test_fecha_hasta_anterior_a_fecha_desde(self, dueno, complejo, cliente_de):
        parametros = _parametros(complejo, fecha_desde='2026-11-30', fecha_hasta='2026-11-01')

        assert 'fecha_hasta' in self._detalle(cliente_de(dueno).get(URL, parametros))

    def test_un_solo_dia_es_valido(self, dueno, complejo, cliente_de):
        parametros = _parametros(complejo, fecha_desde='2026-11-16', fecha_hasta='2026-11-16')

        assert cliente_de(dueno).get(URL, parametros).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('desde,hasta', [
        ('2026-01-01', '2026-12-31'),
        ('2026-01-01', '2027-01-01'),
        ('2028-01-01', '2028-12-31'),
    ])
    def test_admite_hasta_366_dias_inclusive(self, dueno, complejo, cliente_de, desde, hasta):
        parametros = _parametros(complejo, fecha_desde=desde, fecha_hasta=hasta)

        assert cliente_de(dueno).get(URL, parametros).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('desde,hasta', [
        ('2026-01-01', '2027-01-02'),
        ('2028-01-01', '2029-01-01'),
        ('2000-01-01', '2099-12-31'),
    ])
    def test_rechaza_rangos_de_mas_de_366_dias(self, dueno, complejo, cliente_de, desde, hasta):
        parametros = _parametros(complejo, fecha_desde=desde, fecha_hasta=hasta)

        detalle = self._detalle(cliente_de(dueno).get(URL, parametros))

        assert str(MAXIMO_DIAS_REPORTE) in detalle['fecha_hasta']

    def test_admite_rangos_futuros(self, dueno, complejo, cliente_de):
        parametros = _parametros(complejo, fecha_desde='2027-03-01', fecha_hasta='2027-03-31')

        assert cliente_de(dueno).get(URL, parametros).status_code == status.HTTP_200_OK

    def test_criterio_invalido(self, dueno, complejo, cliente_de):
        detalle = self._detalle(cliente_de(dueno).get(URL, _parametros(complejo, criterio='fecha_pago')))

        assert 'criterio' in detalle

    @pytest.mark.parametrize('criterio', ['fecha_turno', 'fecha_creacion', 'fecha_modificacion'])
    def test_criterios_validos(self, dueno, complejo, cliente_de, criterio):
        respuesta = cliente_de(dueno).get(URL, _parametros(complejo, criterio=criterio))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['filtros']['criterio'] == criterio

    def test_la_cancha_de_otro_complejo_se_rechaza(self, dueno, complejo, cancha_ajena, cliente_de):
        detalle = self._detalle(cliente_de(dueno).get(URL, _parametros(complejo, cancha_id=cancha_ajena.id)))

        assert detalle['cancha_id'] == MENSAJE_CANCHA_AJENA

    def test_la_cancha_inexistente_recibe_el_mismo_mensaje(self, dueno, complejo, cancha_ajena, cliente_de):
        parametros = _parametros(complejo, cancha_id=cancha_ajena.id + 999)

        assert self._detalle(cliente_de(dueno).get(URL, parametros))['cancha_id'] == MENSAJE_CANCHA_AJENA

    @pytest.mark.parametrize('estado', [EstadoCancha.EN_MANTENIMIENTO, EstadoCancha.BAJA])
    def test_la_cancha_propia_sin_actividad_conserva_su_historial(self, dueno, complejo, cancha, cliente_de, estado):
        cancha.estado = estado
        cancha.save(update_fields=['estado'])

        respuesta = cliente_de(dueno).get(URL, _parametros(complejo, cancha_id=cancha.id))

        assert respuesta.status_code == status.HTTP_200_OK

    def test_deporte_inexistente(self, dueno, complejo, deporte, cliente_de):
        detalle = self._detalle(cliente_de(dueno).get(URL, _parametros(complejo, deporte_id=deporte.id + 999)))

        assert 'deporte_id' in detalle

    def test_deporte_sin_canchas_en_el_complejo_es_valido(self, dueno, complejo, cancha, cliente_de):
        from core.models import Deporte

        otro = Deporte.objects.exclude(id=cancha.deporte_id).first()

        respuesta = cliente_de(dueno).get(URL, _parametros(complejo, deporte_id=otro.id))

        assert respuesta.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFiltrosAplicados:
    def test_informa_los_filtros_con_el_criterio_por_defecto(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).get(URL, _parametros(complejo))

        assert respuesta.json()['filtros'] == {
            'complejo': complejo.id,
            'fecha_desde': '2026-11-01',
            'fecha_hasta': '2026-11-30',
            'criterio': 'fecha_turno',
            'cancha_id': None,
            'deporte_id': None,
        }

    def test_informa_cancha_y_deporte(self, dueno, complejo, cancha, deporte, cliente_de):
        parametros = _parametros(complejo, cancha_id=cancha.id, deporte_id=deporte.id)

        filtros = cliente_de(dueno).get(URL, parametros).json()['filtros']

        assert (filtros['cancha_id'], filtros['deporte_id']) == (cancha.id, deporte.id)

    def test_el_servicio_valida_sin_pasar_por_la_vista(self, dueno, complejo_ajeno):
        from rest_framework.exceptions import NotFound

        with pytest.raises(NotFound):
            ReporteService.validar_filtros(dueno, {
                'complejo': complejo_ajeno.id,
                'fecha_desde': date(2026, 11, 1),
                'fecha_hasta': date(2026, 11, 30),
                'criterio': 'fecha_turno',
            })


@pytest.fixture
def reservar(cancha, crear_reserva):
    horas = count(8)

    def _reservar(precio, estado=EstadoReserva.CONFIRMADA, fecha=MITAD_DE_MES, en=None, **campos):
        hora = next(horas)
        return crear_reserva(
            en or cancha, fecha, time(hora), time(hora + 1),
            estado=estado, precio_acordado=Decimal(precio), **campos,
        )

    return _reservar


def _fijar(reserva, **fechas_locales):
    Reserva.objects.filter(id=reserva.id).update(**{
        campo: valor.replace(tzinfo=HORA_LOCAL) for campo, valor in fechas_locales.items()
    })


@pytest.mark.django_db
class TestRecaudacion:
    def _recaudacion(self, cliente, complejo, **cambios):
        respuesta = cliente.get(URL, _parametros(complejo, **cambios))
        assert respuesta.status_code == status.HTTP_200_OK
        return respuesta.json()['recaudacion']

    def test_rango_sin_reservas_devuelve_ceros(self, dueno, complejo, cancha, cliente_de):
        assert self._recaudacion(cliente_de(dueno), complejo) == SIN_RECAUDACION

    def test_solo_suman_los_estados_recaudables(self, dueno, complejo, reservar, cliente_de):
        # Un dígito por estado: cualquier estado de más o de menos altera el resultado.
        reservar('1', EstadoReserva.PENDIENTE)
        reservar('10', EstadoReserva.CONFIRMADA)
        reservar('100', EstadoReserva.SENADA)
        reservar('1000', EstadoReserva.CANCELADA_JUGADOR)
        reservar('10000', EstadoReserva.CANCELADA_COMPLEJO)
        reservar('100000', EstadoReserva.AUSENTE)
        reservar('1000000', EstadoReserva.COMPLETADA)
        reservar('20000000', EstadoReserva.BAJA)

        assert self._recaudacion(cliente_de(dueno), complejo) == {'total': '1000110.00', 'senada': '100.00'}

    def test_suma_centavos_sin_redondeos(self, dueno, complejo, reservar, cliente_de):
        reservar('12500.50')
        reservar('0.25', EstadoReserva.SENADA)
        reservar('3333.33', EstadoReserva.COMPLETADA)
        reservar('0.01', EstadoReserva.SENADA)

        assert self._recaudacion(cliente_de(dueno), complejo) == {'total': '15834.09', 'senada': '0.26'}

    def test_incluye_ambos_extremos_del_rango(self, dueno, complejo, reservar, cliente_de):
        reservar('1', fecha=date(2026, 10, 31))
        reservar('10', fecha=date(2026, 11, 1))
        reservar('100', fecha=date(2026, 11, 30))
        reservar('1000', fecha=date(2026, 12, 1))

        assert self._recaudacion(cliente_de(dueno), complejo)['total'] == '110.00'

    def test_un_rango_de_un_dia(self, dueno, complejo, reservar, cliente_de):
        reservar('10', fecha=MITAD_DE_MES)
        reservar('100', fecha=date(2026, 11, 17))

        recaudacion = self._recaudacion(
            cliente_de(dueno), complejo, fecha_desde='2026-11-16', fecha_hasta='2026-11-16',
        )

        assert recaudacion['total'] == '10.00'

    def test_rango_vacio_aunque_haya_reservas_en_otras_fechas(self, dueno, complejo, reservar, cliente_de):
        reservar('500', EstadoReserva.SENADA)

        recaudacion = self._recaudacion(
            cliente_de(dueno), complejo, fecha_desde='2027-01-01', fecha_hasta='2027-01-31',
        )

        assert recaudacion == SIN_RECAUDACION

    def test_no_mezcla_reservas_de_otro_complejo(self, dueno, complejo, cancha_ajena, reservar, cliente_de):
        reservar('10')
        reservar('100', en=cancha_ajena)

        assert self._recaudacion(cliente_de(dueno), complejo)['total'] == '10.00'

    def test_filtra_por_cancha(self, dueno, complejo, cancha, crear_cancha, reservar, cliente_de):
        otra = crear_cancha(complejo, 'Cancha 2')
        reservar('10')
        reservar('100', en=otra)

        assert self._recaudacion(cliente_de(dueno), complejo, cancha_id=otra.id)['total'] == '100.00'

    def test_filtra_por_deporte(self, dueno, complejo, crear_cancha, reservar, cliente_de):
        padel = crear_cancha(complejo, 'Pádel 1', deporte='Pádel')
        reservar('10')
        reservar('100', EstadoReserva.SENADA, en=padel)

        recaudacion = self._recaudacion(cliente_de(dueno), complejo, deporte_id=padel.deporte_id)

        assert recaudacion == {'total': '100.00', 'senada': '100.00'}

    def test_cancha_y_deporte_que_no_coinciden_dan_cero(self, dueno, complejo, cancha, crear_cancha, reservar, cliente_de):
        padel = crear_cancha(complejo, 'Pádel 1', deporte='Pádel')
        reservar('10')

        recaudacion = self._recaudacion(cliente_de(dueno), complejo, cancha_id=cancha.id, deporte_id=padel.deporte_id)

        assert recaudacion == SIN_RECAUDACION

    def test_conserva_lo_recaudado_en_canchas_dadas_de_baja(self, dueno, complejo, cancha, reservar, cliente_de):
        reservar('10', EstadoReserva.COMPLETADA)
        cancha.estado = EstadoCancha.BAJA
        cancha.save(update_fields=['estado'])

        assert self._recaudacion(cliente_de(dueno), complejo)['total'] == '10.00'

    def test_incluye_reservas_manuales_y_fechas_de_turnos_fijos(self, dueno, complejo, reservar, cliente_de):
        reservar('10', usuario=None)
        reservar('100', usuario=None, tipo_ocupacion=TipoOcupacion.TURNO_FIJO)

        assert self._recaudacion(cliente_de(dueno), complejo)['total'] == '110.00'


@pytest.mark.django_db
class TestRecaudacionPorCriterio:
    def _total(self, cliente, complejo, criterio):
        return cliente.get(URL, _parametros(complejo, criterio=criterio)).json()['recaudacion']['total']

    def test_fecha_creacion_toma_cuando_se_registro_y_no_cuando_se_juega(self, dueno, complejo, reservar, cliente_de):
        anticipada = reservar('10', fecha=date(2026, 12, 20))
        _fijar(anticipada, fecha_creacion=datetime(2026, 11, 10, 12, 0))
        jugada_en_rango = reservar('100')
        _fijar(jugada_en_rango, fecha_creacion=datetime(2026, 10, 20, 12, 0))
        cliente = cliente_de(dueno)

        assert self._total(cliente, complejo, 'fecha_creacion') == '10.00'
        assert self._total(cliente, complejo, 'fecha_turno') == '100.00'

    @pytest.mark.parametrize('momento,cuenta', [
        (datetime(2026, 10, 31, 23, 59), False),
        (datetime(2026, 11, 1, 0, 0), True),
        (datetime(2026, 11, 30, 23, 30), True),
        (datetime(2026, 12, 1, 0, 0), False),
    ])
    def test_fecha_creacion_se_corta_en_dias_de_hora_argentina(
        self, dueno, complejo, reservar, cliente_de, momento, cuenta,
    ):
        # 30/11 23:30 en Argentina ya es 1/12 en UTC: el día se decide en hora local.
        _fijar(reservar('10'), fecha_creacion=momento)

        assert self._total(cliente_de(dueno), complejo, 'fecha_creacion') == ('10.00' if cuenta else '0.00')

    @pytest.mark.parametrize('momento,cuenta', [
        (datetime(2026, 10, 31, 23, 59), False),
        (datetime(2026, 11, 1, 0, 0), True),
        (datetime(2026, 11, 30, 23, 59), True),
        (datetime(2026, 12, 1, 0, 0), False),
    ])
    def test_fecha_modificacion_usa_el_ultimo_cambio(self, dueno, complejo, reservar, cliente_de, momento, cuenta):
        _fijar(reservar('10', fecha=date(2026, 9, 5)), fecha_modificacion=momento)

        assert self._total(cliente_de(dueno), complejo, 'fecha_modificacion') == ('10.00' if cuenta else '0.00')
