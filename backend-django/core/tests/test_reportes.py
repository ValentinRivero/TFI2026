from datetime import date, datetime, time, timedelta
from decimal import Decimal
from itertools import count
from zoneinfo import ZoneInfo

import pytest
from rest_framework import status

from core.models import (
    DiaSemana,
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
from core.services import MAXIMO_DIAS_REPORTE, MAXIMO_HORARIOS_RANKING, ReporteService

URL = '/api/reportes/dashboard/'
MENSAJE_CANCHA_AJENA = 'La cancha no pertenece al complejo.'
HORA_LOCAL = ZoneInfo('America/Argentina/Buenos_Aires')
MITAD_DE_MES = date(2026, 11, 16)
SIN_RECAUDACION = {'total': '0.00', 'senada': '0.00'}
SIN_RESERVAS = {
    'pendientes': 0, 'confirmadas': 0, 'senadas': 0,
    'canceladas_jugador': 0, 'canceladas_complejo': 0, 'canceladas_total': 0,
    'ausentes': 0, 'completadas': 0,
}


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
    turnos = count()

    def _reservar(precio, estado=EstadoReserva.CONFIRMADA, fecha=MITAD_DE_MES, en=None, **campos):
        # Quince turnos por día, de 8 a 23; los siguientes pasan al día posterior.
        numero = next(turnos)
        hora = 8 + numero % 15
        return crear_reserva(
            en or cancha, fecha + timedelta(days=numero // 15), time(hora), time(hora + 1),
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


@pytest.mark.django_db
class TestConteosPorEstado:
    def _conteos(self, cliente, complejo, **cambios):
        respuesta = cliente.get(URL, _parametros(complejo, **cambios))
        assert respuesta.status_code == status.HTTP_200_OK
        return respuesta.json()['conteos']

    def _repetir(self, reservar, veces, estado, **campos):
        for _ in range(veces):
            reservar('1000', estado, **campos)

    def test_rango_sin_reservas_devuelve_ceros(self, dueno, complejo, cancha, cliente_de):
        assert self._conteos(cliente_de(dueno), complejo) == SIN_RESERVAS

    def test_cuenta_cada_estado_y_separa_las_canceladas(self, dueno, complejo, reservar, cliente_de):
        # Cantidades distintas por estado: un estado contado en el lugar de otro altera el resultado.
        self._repetir(reservar, 1, EstadoReserva.PENDIENTE)
        self._repetir(reservar, 2, EstadoReserva.CONFIRMADA)
        self._repetir(reservar, 3, EstadoReserva.SENADA)
        self._repetir(reservar, 4, EstadoReserva.CANCELADA_JUGADOR)
        self._repetir(reservar, 5, EstadoReserva.CANCELADA_COMPLEJO)
        self._repetir(reservar, 6, EstadoReserva.AUSENTE)
        self._repetir(reservar, 7, EstadoReserva.COMPLETADA)
        self._repetir(reservar, 2, EstadoReserva.BAJA)

        assert self._conteos(cliente_de(dueno), complejo) == {
            'pendientes': 1, 'confirmadas': 2, 'senadas': 3,
            'canceladas_jugador': 4, 'canceladas_complejo': 5, 'canceladas_total': 9,
            'ausentes': 6, 'completadas': 7,
        }

    def test_aplica_los_mismos_filtros_que_la_recaudacion(
        self, dueno, complejo, cancha, cancha_ajena, crear_cancha, reservar, cliente_de,
    ):
        otra = crear_cancha(complejo, 'Cancha 2')
        reservar('1000', EstadoReserva.CANCELADA_JUGADOR)
        reservar('1000', EstadoReserva.CANCELADA_JUGADOR, en=otra)
        reservar('1000', EstadoReserva.CANCELADA_JUGADOR, en=cancha_ajena)
        reservar('1000', EstadoReserva.CANCELADA_JUGADOR, fecha=date(2026, 12, 1))
        cliente = cliente_de(dueno)

        assert self._conteos(cliente, complejo)['canceladas_jugador'] == 2
        assert self._conteos(cliente, complejo, cancha_id=otra.id)['canceladas_jugador'] == 1

    def test_las_cancelaciones_del_mes_por_fecha_de_modificacion(self, dueno, complejo, reservar, cliente_de):
        cancelada_para_diciembre = reservar('1000', EstadoReserva.CANCELADA_COMPLEJO, fecha=date(2026, 12, 20))
        _fijar(cancelada_para_diciembre, fecha_modificacion=datetime(2026, 11, 12, 9, 0))
        cliente = cliente_de(dueno)

        assert self._conteos(cliente, complejo, criterio='fecha_modificacion')['canceladas_complejo'] == 1
        assert self._conteos(cliente, complejo)['canceladas_complejo'] == 0

    def test_conteos_y_recaudacion_salen_de_las_mismas_reservas(self, dueno, complejo, reservar, cliente_de):
        reservar('100', EstadoReserva.SENADA)
        reservar('200', EstadoReserva.SENADA)
        reservar('50', EstadoReserva.AUSENTE)

        cuerpo = cliente_de(dueno).get(URL, _parametros(complejo)).json()

        assert cuerpo['conteos']['senadas'] == 2
        assert cuerpo['recaudacion'] == {'total': '300.00', 'senada': '300.00'}


LUNES_16, MIERCOLES_18, DOMINGO_22 = date(2026, 11, 16), date(2026, 11, 18), date(2026, 11, 22)
SEMANA = {'fecha_desde': '2026-11-16', 'fecha_hasta': '2026-11-22'}
SOLO_LUNES = {'fecha_desde': '2026-11-16', 'fecha_hasta': '2026-11-16'}
DIAS_HABILES = range(DiaSemana.LUNES, DiaSemana.SABADO)


@pytest.fixture
def abrir(crear_horario):
    def _abrir(cancha, desde, hasta, dias=DIAS_HABILES):
        for dia in dias:
            crear_horario(cancha, dia, desde, hasta)

    return _abrir


@pytest.fixture
def ocupar(crear_reserva):
    def _ocupar(cancha, fecha, desde, hasta, estado=EstadoReserva.CONFIRMADA):
        return crear_reserva(cancha, fecha, desde, hasta, estado=estado)

    return _ocupar


def _ocupacion(cliente, complejo, rango=SEMANA, **cambios):
    respuesta = cliente.get(URL, _parametros(complejo, **rango, **cambios))
    assert respuesta.status_code == status.HTTP_200_OK
    return respuesta.json()['ocupacion']


def _de(ocupacion, cancha):
    return next(fila for fila in ocupacion if fila['cancha_id'] == cancha.id)


@pytest.mark.django_db
class TestOcupacionPorCancha:
    def test_descuenta_el_dia_cerrado_por_excepcion(
        self, dueno, complejo, cancha, abrir, ocupar, crear_excepcion_horaria, cliente_de,
    ):
        # 18 a 23 de lunes a viernes, turnos de 60: 5 turnos por día, 25 en la semana; el feriado deja 20.
        abrir(cancha, time(18), time(23))
        crear_excepcion_horaria(complejo, MIERCOLES_18)
        turnos_por_dia = {16: (18, 19, 20), 17: (18, 19), 19: (18, 19), 20: (18, 19, 20)}
        for dia, horas in turnos_por_dia.items():
            for hora in horas:
                ocupar(cancha, date(2026, 11, dia), time(hora), time(hora + 1))

        assert _de(_ocupacion(cliente_de(dueno), complejo), cancha) == {
            'cancha_id': cancha.id, 'cancha': cancha.nombre,
            'minutos_ofertables': 1200, 'minutos_ocupados': 600, 'porcentaje': 50.0,
        }

    def test_la_oferta_son_turnos_completos_de_la_grilla(self, dueno, complejo, cancha, abrir, ocupar, cliente_de):
        # Turnos de 90 entre 18 y 23: 18:00, 19:30 y 21:00; la media hora restante no se ofrece.
        cancha.duracion_turno_min = 90
        cancha.save(update_fields=['duracion_turno_min'])
        abrir(cancha, time(18), time(23), dias=[DiaSemana.LUNES])
        ocupar(cancha, LUNES_16, time(19, 30), time(21))

        fila = _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)

        assert (fila['minutos_ofertables'], fila['minutos_ocupados'], fila['porcentaje']) == (270, 90, 33.33)

    def test_suma_los_rangos_de_un_dia_con_cortes(self, dueno, complejo, cancha, crear_horario, cliente_de):
        crear_horario(cancha, DiaSemana.LUNES, time(8), time(12))
        crear_horario(cancha, DiaSemana.LUNES, time(17), time(21))

        assert _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)['minutos_ofertables'] == 480

    @pytest.mark.parametrize('desde,hasta,ofertables', [
        (time(10), time(11), 420),
        (time(10, 30), time(11, 30), 360),
    ])
    def test_una_franja_cierra_cada_turno_que_toca(
        self, dueno, complejo, cancha, crear_horario, crear_excepcion_horaria, cliente_de, desde, hasta, ofertables,
    ):
        crear_horario(cancha, DiaSemana.LUNES, time(8), time(12))
        crear_horario(cancha, DiaSemana.LUNES, time(17), time(21))
        crear_excepcion_horaria(complejo, LUNES_16, cancha=cancha, inicio=desde, fin=hasta)

        fila = _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)

        assert fila['minutos_ofertables'] == ofertables

    def test_una_excepcion_que_empieza_antes_del_rango(
        self, dueno, complejo, cancha, abrir, crear_excepcion_horaria, cliente_de,
    ):
        abrir(cancha, time(18), time(23))
        crear_excepcion_horaria(complejo, date(2026, 11, 10), date(2026, 11, 17))

        assert _de(_ocupacion(cliente_de(dueno), complejo), cancha)['minutos_ofertables'] == 900

    def test_ignora_excepciones_dadas_de_baja_de_otra_cancha_o_de_otro_complejo(
        self, dueno, complejo, complejo_ajeno, cancha, crear_cancha, abrir, crear_excepcion_horaria, cliente_de,
    ):
        abrir(cancha, time(18), time(23), dias=[DiaSemana.LUNES])
        crear_excepcion_horaria(complejo, LUNES_16).desactivar()
        crear_excepcion_horaria(complejo, LUNES_16, cancha=crear_cancha(complejo, 'Cancha 2'))
        crear_excepcion_horaria(complejo_ajeno, LUNES_16)

        assert _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)['minutos_ofertables'] == 300

    def test_un_horario_dado_de_baja_no_se_ofrece(self, dueno, complejo, cancha, crear_horario, cliente_de):
        crear_horario(cancha, DiaSemana.LUNES, time(18), time(23))
        crear_horario(cancha, DiaSemana.LUNES, time(8), time(12)).desactivar()

        assert _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)['minutos_ofertables'] == 300

    @pytest.mark.parametrize('estado,ocupa', [
        (EstadoReserva.PENDIENTE, True),
        (EstadoReserva.CONFIRMADA, True),
        (EstadoReserva.SENADA, True),
        (EstadoReserva.COMPLETADA, True),
        (EstadoReserva.CANCELADA_JUGADOR, False),
        (EstadoReserva.CANCELADA_COMPLEJO, False),
        (EstadoReserva.AUSENTE, False),
        (EstadoReserva.BAJA, False),
    ])
    def test_solo_ocupan_los_estados_ocupantes(
        self, dueno, complejo, cancha, abrir, ocupar, cliente_de, estado, ocupa,
    ):
        abrir(cancha, time(18), time(23), dias=[DiaSemana.LUNES])
        ocupar(cancha, LUNES_16, time(18), time(19), estado=estado)

        fila = _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)

        assert (fila['minutos_ocupados'], fila['porcentaje']) == ((60, 20.0) if ocupa else (0, 0.0))

    def test_un_turno_tomado_antes_de_un_cierre_sigue_ofrecido(
        self, dueno, complejo, cancha, abrir, ocupar, crear_excepcion_horaria, cliente_de,
    ):
        abrir(cancha, time(18), time(23), dias=[DiaSemana.LUNES])
        ocupar(cancha, LUNES_16, time(19), time(20))
        crear_excepcion_horaria(complejo, LUNES_16)

        fila = _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)

        assert (fila['minutos_ofertables'], fila['minutos_ocupados'], fila['porcentaje']) == (60, 60, 100.0)

    def test_una_reserva_fuera_de_la_grilla_actual_suma_a_la_oferta(
        self, dueno, complejo, cancha, abrir, ocupar, cliente_de,
    ):
        abrir(cancha, time(18), time(23), dias=[DiaSemana.LUNES])
        ocupar(cancha, LUNES_16, time(15), time(16), estado=EstadoReserva.COMPLETADA)
        ocupar(cancha, LUNES_16, time(22, 30), time(23, 30))

        fila = _de(_ocupacion(cliente_de(dueno), complejo, rango=SOLO_LUNES), cancha)

        assert (fila['minutos_ofertables'], fila['minutos_ocupados'], fila['porcentaje']) == (390, 120, 30.77)

    def test_rango_sin_reservas_da_cero_por_ciento(self, dueno, complejo, cancha, abrir, cliente_de):
        abrir(cancha, time(18), time(23))

        assert _de(_ocupacion(cliente_de(dueno), complejo), cancha)['porcentaje'] == 0.0

    def test_cancha_sin_horarios_no_tiene_porcentaje(self, dueno, complejo, cancha, cliente_de):
        assert _de(_ocupacion(cliente_de(dueno), complejo), cancha) == {
            'cancha_id': cancha.id, 'cancha': cancha.nombre,
            'minutos_ofertables': 0, 'minutos_ocupados': 0, 'porcentaje': None,
        }

    def test_cancha_inactiva_con_reservas_informa_solo_lo_ocupado(
        self, dueno, complejo, cancha, crear_cancha, abrir, ocupar, cliente_de,
    ):
        en_mantenimiento = crear_cancha(complejo, 'Cancha 2', estado=EstadoCancha.EN_MANTENIMIENTO)
        abrir(en_mantenimiento, time(18), time(23))
        ocupar(en_mantenimiento, LUNES_16, time(18), time(19), estado=EstadoReserva.COMPLETADA)
        crear_cancha(complejo, 'Cancha 3', estado=EstadoCancha.BAJA)

        ocupacion = _ocupacion(cliente_de(dueno), complejo)

        assert [fila['cancha'] for fila in ocupacion] == ['Cancha 2', 'Cancha Propia']
        assert _de(ocupacion, en_mantenimiento) == {
            'cancha_id': en_mantenimiento.id, 'cancha': 'Cancha 2',
            'minutos_ofertables': None, 'minutos_ocupados': 60, 'porcentaje': None,
        }

    def test_aplica_los_filtros_de_cancha_y_deporte(
        self, dueno, complejo, cancha, cancha_ajena, crear_cancha, cliente_de,
    ):
        padel = crear_cancha(complejo, 'Pádel 1', deporte='Pádel')
        cliente = cliente_de(dueno)

        assert {fila['cancha_id'] for fila in _ocupacion(cliente, complejo)} == {cancha.id, padel.id}
        assert [fila['cancha_id'] for fila in _ocupacion(cliente, complejo, cancha_id=cancha.id)] == [cancha.id]
        assert [fila['cancha_id'] for fila in _ocupacion(cliente, complejo, deporte_id=padel.deporte_id)] == [padel.id]

    @pytest.mark.parametrize('criterio', ['fecha_creacion', 'fecha_modificacion'])
    def test_sin_dias_de_juego_no_hay_ocupacion(self, dueno, complejo, cancha, abrir, cliente_de, criterio):
        abrir(cancha, time(18), time(23))

        assert _ocupacion(cliente_de(dueno), complejo, criterio=criterio) is None

    def test_cancha_de_un_deporte_dado_de_baja_no_tiene_oferta(
        self, dueno, complejo, cancha, abrir, ocupar, cliente_de,
    ):
        abrir(cancha, time(18), time(23))
        ocupar(cancha, LUNES_16, time(18), time(19))
        cancha.deporte.desactivar()

        fila = _de(_ocupacion(cliente_de(dueno), complejo), cancha)

        assert (fila['minutos_ofertables'], fila['minutos_ocupados'], fila['porcentaje']) == (None, 60, None)


@pytest.mark.django_db
class TestRankingDeHorarios:
    def _ranking(self, cliente, complejo, **cambios):
        respuesta = cliente.get(URL, _parametros(complejo, **cambios))
        assert respuesta.status_code == status.HTTP_200_OK
        return respuesta.json()['ranking_horarios']

    def _tomar(self, ocupar, cancha, hora, veces, estado=EstadoReserva.CONFIRMADA, minuto=0):
        # Un día distinto por reserva: la misma hora no se repite en la misma cancha y fecha.
        for dia in range(1, veces + 1):
            ocupar(cancha, date(2026, 11, dia), time(hora, minuto), time(hora + 1, minuto), estado=estado)

    def test_rango_sin_reservas_devuelve_lista_vacia(self, dueno, complejo, cancha, cliente_de):
        assert self._ranking(cliente_de(dueno), complejo) == []

    def test_ordena_por_cantidad_y_desempata_por_hora(self, dueno, complejo, cancha, ocupar, cliente_de):
        self._tomar(ocupar, cancha, 18, 2)
        self._tomar(ocupar, cancha, 20, 5)
        self._tomar(ocupar, cancha, 21, 2)
        self._tomar(ocupar, cancha, 19, 3, minuto=30)

        assert self._ranking(cliente_de(dueno), complejo) == [
            {'hora_inicio': '20:00:00', 'reservas': 5},
            {'hora_inicio': '19:30:00', 'reservas': 3},
            {'hora_inicio': '18:00:00', 'reservas': 2},
            {'hora_inicio': '21:00:00', 'reservas': 2},
        ]

    @pytest.mark.parametrize('estado,cuenta', [
        (EstadoReserva.PENDIENTE, True),
        (EstadoReserva.CONFIRMADA, True),
        (EstadoReserva.SENADA, True),
        (EstadoReserva.COMPLETADA, True),
        (EstadoReserva.CANCELADA_JUGADOR, False),
        (EstadoReserva.CANCELADA_COMPLEJO, False),
        (EstadoReserva.AUSENTE, False),
        (EstadoReserva.BAJA, False),
    ])
    def test_solo_cuentan_los_estados_ocupantes(self, dueno, complejo, cancha, ocupar, cliente_de, estado, cuenta):
        self._tomar(ocupar, cancha, 18, 1, estado=estado)

        esperado = [{'hora_inicio': '18:00:00', 'reservas': 1}] if cuenta else []
        assert self._ranking(cliente_de(dueno), complejo) == esperado

    def test_suma_la_misma_hora_de_todas_las_canchas(
        self, dueno, complejo, cancha, cancha_ajena, crear_cancha, ocupar, cliente_de,
    ):
        otra = crear_cancha(complejo, 'Cancha 2')
        self._tomar(ocupar, cancha, 18, 2)
        self._tomar(ocupar, otra, 18, 1)
        self._tomar(ocupar, cancha_ajena, 18, 4)
        cliente = cliente_de(dueno)

        assert self._ranking(cliente, complejo) == [{'hora_inicio': '18:00:00', 'reservas': 3}]
        assert self._ranking(cliente, complejo, cancha_id=otra.id) == [{'hora_inicio': '18:00:00', 'reservas': 1}]

    def test_devuelve_como_maximo_los_diez_primeros(self, dueno, complejo, cancha, ocupar, cliente_de):
        # De 8 a 19, doce horarios con una reserva cada uno salvo el de las 19, con dos: el corte deja afuera 18 y 17.
        for hora in range(8, 20):
            self._tomar(ocupar, cancha, hora, 2 if hora == 19 else 1)

        ranking = self._ranking(cliente_de(dueno), complejo)

        assert len(ranking) == MAXIMO_HORARIOS_RANKING
        assert ranking[0] == {'hora_inicio': '19:00:00', 'reservas': 2}
        assert [fila['hora_inicio'] for fila in ranking[1:]] == [f'{hora:02d}:00:00' for hora in range(8, 17)]

    def test_respeta_el_criterio_temporal(self, dueno, complejo, cancha, ocupar, cliente_de):
        reserva = ocupar(cancha, date(2026, 12, 20), time(18), time(19))
        _fijar(reserva, fecha_creacion=datetime(2026, 11, 3, 10, 0))
        cliente = cliente_de(dueno)

        assert self._ranking(cliente, complejo) == []
        assert self._ranking(cliente, complejo, criterio='fecha_creacion') == [
            {'hora_inicio': '18:00:00', 'reservas': 1},
        ]
