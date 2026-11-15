from datetime import time, timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound

from core.models import (
    AlcanceExcepcion,
    EstadoCancha,
    EstadoRegistro,
    ExcepcionHoraria,
    LogAuditoria,
    RolPermiso,
    TipoEventoAuditoria,
    TipoMotivoExcepcion,
)
from core.services import DifusionGrillaService, ExcepcionHorariaService

URL = '/api/excepciones/'


def _dias(cantidad):
    return timezone.localdate() + timedelta(days=cantidad)


@pytest.fixture
def cancha(complejo, crear_cancha):
    return crear_cancha(complejo, 'Cancha Propia')


@pytest.fixture
def cancha_ajena(complejo_ajeno, crear_cancha):
    return crear_cancha(complejo_ajeno, 'Cancha Ajena')


@pytest.fixture
def crear_excepcion(dueno):
    def _crear(complejo, cancha=None, desde=1, hasta=None, **campos):
        campos.setdefault('tipo_motivo', TipoMotivoExcepcion.MANTENIMIENTO)
        campos.setdefault('creado_por', dueno)
        if 'hora_inicio' in campos:
            campos.setdefault('es_dia_completo', AlcanceExcepcion.FRANJA_HORARIA)
        return ExcepcionHoraria.objects.create(
            complejo=complejo, cancha=cancha, fecha_inicio=_dias(desde),
            fecha_fin=_dias(desde if hasta is None else hasta), **campos,
        )

    return _crear


def _dia_completo(complejo, cancha=None, **cambios):
    datos = {
        'complejo': complejo.id,
        'cancha': cancha.id if cancha else None,
        'fecha_inicio': _dias(3).isoformat(),
        'fecha_fin': _dias(3).isoformat(),
        'es_dia_completo': AlcanceExcepcion.DIA_COMPLETO,
        'tipo_motivo': TipoMotivoExcepcion.FERIADO,
    }
    datos.update(cambios)
    return datos


def _franja(complejo, cancha=None, **cambios):
    datos = _dia_completo(
        complejo, cancha, es_dia_completo=AlcanceExcepcion.FRANJA_HORARIA,
        hora_inicio='14:00', hora_fin='17:00', tipo_motivo=TipoMotivoExcepcion.MANTENIMIENTO,
    )
    datos.update(cambios)
    return datos


def _ids(respuesta):
    return [excepcion['id'] for excepcion in respuesta.json()['results']]


class TestConsultaDeExcepciones:
    def test_dueno_lista_las_de_su_complejo_paginadas(self, dueno, complejo, cancha, crear_excepcion, cliente_de):
        global_ = crear_excepcion(complejo)
        de_cancha = crear_excepcion(complejo, cancha, desde=2, hora_inicio=time(14, 0), hora_fin=time(17, 0))

        respuesta = cliente_de(dueno).get(URL, {'complejo': complejo.id})

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert set(cuerpo) == {'count', 'next', 'previous', 'results'}
        assert _ids(respuesta) == [global_.id, de_cancha.id]
        primera, segunda = cuerpo['results']
        assert primera['cancha'] is None and primera['cancha_nombre'] is None
        assert primera['es_dia_completo_nombre'] == 'Día completo'
        assert segunda['cancha_nombre'] == 'Cancha Propia'
        assert segunda['hora_inicio'] == '14:00:00'
        assert segunda['tipo_motivo_nombre'] == 'Mantenimiento'

    def test_pagina_de_a_20(self, dueno, complejo, crear_excepcion, cliente_de):
        for dia in range(21):
            crear_excepcion(complejo, desde=dia)

        cuerpo = cliente_de(dueno).get(URL).json()

        assert cuerpo['count'] == 21
        assert len(cuerpo['results']) == 20
        assert cuerpo['next'] is not None

    def test_no_expone_quien_la_registro(self, dueno, complejo, crear_excepcion, cliente_de):
        crear_excepcion(complejo)

        (excepcion,) = cliente_de(dueno).get(URL).json()['results']

        assert 'creado_por' not in excepcion
        assert 'dueno@talibre.test' not in str(excepcion)

    def test_operador_consulta_las_de_su_complejo(self, operador, complejo, complejo_ajeno, crear_excepcion, cliente_de):
        propia = crear_excepcion(complejo)
        crear_excepcion(complejo_ajeno)

        assert _ids(cliente_de(operador).get(URL)) == [propia.id]

    def test_superadmin_ve_todas(self, superadmin, complejo, complejo_ajeno, crear_excepcion, cliente_de):
        crear_excepcion(complejo)
        crear_excepcion(complejo_ajeno)

        assert cliente_de(superadmin).get(URL).json()['count'] == 2

    def test_no_lista_las_dadas_de_baja(self, dueno, complejo, crear_excepcion, cliente_de):
        crear_excepcion(complejo).desactivar()

        assert cliente_de(dueno).get(URL).json()['count'] == 0

    def test_complejo_ajeno_responde_404(self, dueno, complejo_ajeno, cliente_de):
        assert cliente_de(dueno).get(URL, {'complejo': complejo_ajeno.id}).status_code == status.HTTP_404_NOT_FOUND

    def test_cancha_ajena_responde_404(self, dueno, cancha_ajena, cliente_de):
        assert cliente_de(dueno).get(URL, {'cancha': cancha_ajena.id}).status_code == status.HTTP_404_NOT_FOUND

    def test_detalle_ajeno_responde_404(self, dueno, complejo_ajeno, crear_excepcion, cliente_de):
        ajena = crear_excepcion(complejo_ajeno)

        assert cliente_de(dueno).get(f'{URL}{ajena.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_filtrar_por_cancha_incluye_las_globales_del_complejo(
        self, dueno, complejo, cancha, crear_cancha, crear_excepcion, cliente_de,
    ):
        otra = crear_cancha(complejo, 'Cancha 2')
        global_ = crear_excepcion(complejo, desde=1)
        propia = crear_excepcion(complejo, cancha, desde=2)
        crear_excepcion(complejo, otra, desde=3)

        assert _ids(cliente_de(dueno).get(URL, {'cancha': cancha.id})) == [global_.id, propia.id]

    def test_filtra_por_vigencia(self, dueno, complejo, crear_excepcion, cliente_de):
        finalizada = crear_excepcion(complejo, desde=-5, hasta=-1)
        en_curso = crear_excepcion(complejo, desde=-2, hasta=0)
        futura = crear_excepcion(complejo, desde=4)
        cliente = cliente_de(dueno)

        assert _ids(cliente.get(URL, {'vigencia': 'vigentes'})) == [en_curso.id, futura.id]
        assert _ids(cliente.get(URL, {'vigencia': 'finalizadas'})) == [finalizada.id]

    def test_filtra_por_fecha_cubierta(self, dueno, complejo, crear_excepcion, cliente_de):
        rango = crear_excepcion(complejo, desde=2, hasta=6)
        crear_excepcion(complejo, desde=7)

        assert _ids(cliente_de(dueno).get(URL, {'fecha': _dias(6).isoformat()})) == [rango.id]

    def test_filtra_por_motivo(self, dueno, complejo, crear_excepcion, cliente_de):
        feriado = crear_excepcion(complejo, tipo_motivo=TipoMotivoExcepcion.FERIADO)
        crear_excepcion(complejo, tipo_motivo=TipoMotivoExcepcion.CLIMA)

        assert _ids(cliente_de(dueno).get(URL, {'tipo_motivo': TipoMotivoExcepcion.FERIADO})) == [feriado.id]

    @pytest.mark.parametrize('parametros', [{'vigencia': 'todas'}, {'fecha': '18/11/2026'}, {'tipo_motivo': 9}])
    def test_filtro_invalido_responde_400(self, dueno, cliente_de, parametros):
        assert cliente_de(dueno).get(URL, parametros).status_code == status.HTTP_400_BAD_REQUEST

    def test_jugador_recibe_403(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN

    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED


class TestAltaDeExcepciones:
    def test_dueno_registra_un_cierre_global_de_dia_completo(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _dia_completo(complejo), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        excepcion = ExcepcionHoraria.objects.get(id=respuesta.json()['id'])
        assert excepcion.cancha is None
        assert excepcion.es_dia_completo == AlcanceExcepcion.DIA_COMPLETO
        assert excepcion.hora_inicio is None and excepcion.hora_fin is None
        assert excepcion.creado_por == dueno
        assert excepcion.estado == EstadoRegistro.ACTIVO

    def test_operador_registra_una_franja_de_una_cancha(self, operador, complejo, cancha, cliente_de):
        respuesta = cliente_de(operador).post(URL, _franja(complejo, cancha), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        excepcion = ExcepcionHoraria.objects.get(id=respuesta.json()['id'])
        assert excepcion.cancha == cancha
        assert (excepcion.hora_inicio, excepcion.hora_fin) == (time(14, 0), time(17, 0))
        assert excepcion.creado_por == operador

    def test_superadmin_registra_en_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        assert cliente_de(superadmin).post(
            URL, _dia_completo(complejo_ajeno), format='json',
        ).status_code == status.HTTP_201_CREATED

    def test_admite_un_rango_de_varios_dias_que_empieza_hoy(self, dueno, complejo, cliente_de):
        datos = _dia_completo(complejo, fecha_inicio=_dias(0).isoformat(), fecha_fin=_dias(2).isoformat())

        assert cliente_de(dueno).post(URL, datos, format='json').status_code == status.HTTP_201_CREATED

    def test_dia_completo_con_horario_responde_400(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _dia_completo(complejo, hora_inicio='10:00'), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_inicio' in respuesta.json()['detail']

    def test_dia_completo_con_horas_nulas_es_valido(self, dueno, complejo, cliente_de):
        datos = _dia_completo(complejo, hora_inicio=None, hora_fin=None)

        assert cliente_de(dueno).post(URL, datos, format='json').status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize('faltante', ['hora_inicio', 'hora_fin'])
    def test_franja_sin_horas_responde_400(self, dueno, complejo, cliente_de, faltante):
        datos = _franja(complejo)
        del datos[faltante]

        respuesta = cliente_de(dueno).post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert faltante in respuesta.json()['detail']

    @pytest.mark.parametrize('inicio, fin', [('17:00', '14:00'), ('14:00', '14:00')])
    def test_franja_con_fin_no_posterior_responde_400(self, dueno, complejo, cliente_de, inicio, fin):
        respuesta = cliente_de(dueno).post(URL, _franja(complejo, hora_inicio=inicio, hora_fin=fin), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_fin' in respuesta.json()['detail']

    def test_fecha_fin_anterior_al_inicio_responde_400(self, dueno, complejo, cliente_de):
        datos = _dia_completo(complejo, fecha_inicio=_dias(5).isoformat(), fecha_fin=_dias(4).isoformat())

        respuesta = cliente_de(dueno).post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_fin' in respuesta.json()['detail']

    def test_no_se_registran_excepciones_pasadas(self, dueno, complejo, cliente_de):
        datos = _dia_completo(complejo, fecha_inicio=_dias(-1).isoformat(), fecha_fin=_dias(1).isoformat())

        respuesta = cliente_de(dueno).post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'fecha_inicio' in respuesta.json()['detail']

    def test_el_rango_tiene_un_maximo_de_dias(self, dueno, complejo, cliente_de, settings):
        cliente = cliente_de(dueno)
        limite = _dia_completo(complejo, fecha_inicio=_dias(1).isoformat(),
                               fecha_fin=_dias(settings.RANGO_MAXIMO_DIAS).isoformat())
        excedido = _dia_completo(complejo, fecha_inicio=_dias(1).isoformat(),
                                 fecha_fin=_dias(settings.RANGO_MAXIMO_DIAS + 1).isoformat())

        assert cliente.post(URL, limite, format='json').status_code == status.HTTP_201_CREATED
        assert cliente.post(URL, excedido, format='json').status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize('campo, valor', [
        ('es_dia_completo', 2), ('tipo_motivo', 0), ('fecha_inicio', '18/11/2026'),
    ])
    def test_valores_invalidos_responden_400(self, dueno, complejo, cliente_de, campo, valor):
        respuesta = cliente_de(dueno).post(URL, _dia_completo(complejo, **{campo: valor}), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_cancha_de_otro_complejo_responde_400(self, superadmin, complejo, cancha_ajena, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, _franja(complejo, cancha_ajena), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cancha' in respuesta.json()['detail']
        assert not ExcepcionHoraria.objects.exists()

    def test_cancha_en_mantenimiento_responde_400(self, dueno, complejo, cancha, cliente_de):
        cancha.estado = EstadoCancha.EN_MANTENIMIENTO
        cancha.save()

        respuesta = cliente_de(dueno).post(URL, _franja(complejo, cancha), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cancha' in respuesta.json()['detail']

    def test_cancha_dada_de_baja_responde_400(self, dueno, complejo, cancha, cliente_de):
        cancha.desactivar()

        assert cliente_de(dueno).post(
            URL, _franja(complejo, cancha), format='json',
        ).status_code == status.HTTP_400_BAD_REQUEST

    def test_complejo_ajeno_responde_403(self, dueno, complejo_ajeno, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _dia_completo(complejo_ajeno), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not ExcepcionHoraria.objects.exists()

    def test_operador_no_registra_en_otro_complejo(self, operador, complejo_ajeno, cliente_de):
        assert cliente_de(operador).post(
            URL, _dia_completo(complejo_ajeno), format='json',
        ).status_code == status.HTTP_403_FORBIDDEN

    def test_jugador_recibe_403(self, jugador, complejo, cliente_de):
        assert cliente_de(jugador).post(URL, _dia_completo(complejo), format='json').status_code == status.HTTP_403_FORBIDDEN

    def test_sin_gestionar_excepciones_recibe_403(self, operador, complejo, cliente_de):
        RolPermiso.objects.get(rol__nombre='OPERADOR_COMPLEJO', permiso__codigo='gestionar_excepciones').desactivar()

        assert cliente_de(operador).post(URL, _dia_completo(complejo), format='json').status_code == status.HTTP_403_FORBIDDEN

    def test_la_descripcion_se_sanitiza(self, dueno, complejo, cliente_de):
        datos = _dia_completo(complejo, descripcion='<script>alert(1)</script>Corte de <b>luz</b>')

        respuesta = cliente_de(dueno).post(URL, datos, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['descripcion'] == 'Corte de luz'
        assert ExcepcionHoraria.objects.get().descripcion == 'Corte de luz'

    def test_la_edicion_no_esta_disponible(self, dueno, complejo, crear_excepcion, cliente_de):
        excepcion = crear_excepcion(complejo)

        respuesta = cliente_de(dueno).patch(f'{URL}{excepcion.id}/', {'tipo_motivo': 2}, format='json')

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestAuditoriaDeExcepciones:
    def test_el_alta_se_audita_sin_la_descripcion(self, dueno, complejo, cancha, cliente_de, log_seguridad):
        datos = _franja(complejo, cancha, descripcion='Cumpleaños de Teodoro Arrúa, tel 3777 000999')

        respuesta = cliente_de(dueno).post(URL, datos, format='json')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ALTA_EXCEPCION)
        assert log.usuario == dueno
        assert log.complejo == complejo
        assert f'Excepción id {respuesta.json()["id"]}' in log.detalle
        assert f'cancha id {cancha.id}' in log.detalle
        assert '14:00 a 17:00' in log.detalle
        assert 'Mantenimiento' in log.detalle
        for texto in ('Teodoro', 'Arrúa', '3777 000999'):
            assert texto not in log.detalle
            assert texto not in log_seguridad.text

    def test_el_alta_global_indica_todo_el_complejo(self, dueno, complejo, cliente_de):
        cliente_de(dueno).post(URL, _dia_completo(complejo), format='json')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ALTA_EXCEPCION)
        assert 'todo el complejo' in log.detalle
        assert 'día completo' in log.detalle

    def test_un_alta_rechazada_no_se_audita(self, dueno, complejo, cliente_de):
        cliente_de(dueno).post(URL, _dia_completo(complejo, fecha_inicio=_dias(-3).isoformat()), format='json')

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ALTA_EXCEPCION).exists()

    def test_la_baja_se_audita(self, operador, complejo, crear_excepcion, cliente_de):
        excepcion = crear_excepcion(complejo, descripcion='Texto libre del personal')

        cliente_de(operador).delete(f'{URL}{excepcion.id}/')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.BAJA_EXCEPCION)
        assert log.usuario == operador
        assert log.complejo == complejo
        assert f'Excepción id {excepcion.id}' in log.detalle
        assert 'Texto libre' not in log.detalle


class TestBajaLogicaDeExcepciones:
    def test_la_baja_es_logica(self, dueno, complejo, crear_excepcion, cliente_de):
        excepcion = crear_excepcion(complejo)

        respuesta = cliente_de(dueno).delete(f'{URL}{excepcion.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        excepcion.refresh_from_db()
        assert excepcion.estado == EstadoRegistro.BAJA
        assert cliente_de(dueno).get(f'{URL}{excepcion.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_una_segunda_baja_responde_404(self, dueno, complejo, crear_excepcion, cliente_de):
        excepcion = crear_excepcion(complejo)
        cliente = cliente_de(dueno)
        cliente.delete(f'{URL}{excepcion.id}/')

        assert cliente.delete(f'{URL}{excepcion.id}/').status_code == status.HTTP_404_NOT_FOUND
        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.BAJA_EXCEPCION).count() == 1

    def test_excepcion_ajena_responde_404(self, dueno, complejo_ajeno, crear_excepcion, cliente_de):
        ajena = crear_excepcion(complejo_ajeno)

        assert cliente_de(dueno).delete(f'{URL}{ajena.id}/').status_code == status.HTTP_404_NOT_FOUND
        ajena.refresh_from_db()
        assert ajena.estado == EstadoRegistro.ACTIVO

    def test_superadmin_da_de_baja_cualquiera(self, superadmin, complejo_ajeno, crear_excepcion, cliente_de):
        ajena = crear_excepcion(complejo_ajeno)

        assert cliente_de(superadmin).delete(f'{URL}{ajena.id}/').status_code == status.HTTP_204_NO_CONTENT

    def test_jugador_recibe_403(self, jugador, complejo, crear_excepcion, cliente_de):
        excepcion = crear_excepcion(complejo)

        assert cliente_de(jugador).delete(f'{URL}{excepcion.id}/').status_code == status.HTTP_403_FORBIDDEN

    def test_una_baja_simultanea_ya_aplicada_no_se_repite(self, dueno, complejo, crear_excepcion):
        # Otra petición dio de baja la excepción entre la lectura de la vista y el bloqueo de la fila.
        excepcion = crear_excepcion(complejo)
        excepcion.desactivar()

        with pytest.raises(NotFound):
            ExcepcionHorariaService.dar_de_baja(excepcion.id, dueno, None)

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.BAJA_EXCEPCION).exists()


class TestDifusionDeExcepciones:
    def test_el_alta_se_anuncia_recien_al_confirmar_la_transaccion(
        self, dueno, complejo, cancha, cliente_de, django_capture_on_commit_callbacks,
    ):
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks() as pendientes:
                respuesta = cliente_de(dueno).post(URL, _franja(complejo, cancha), format='json')
                publicar.assert_not_called()

            assert len(pendientes) == 1
            pendientes[0]()

        publicar.assert_called_once_with(complejo.id, {
            'event': 'grilla_actualizada',
            'cancha_id': cancha.id,
            'fecha_desde': _dias(3).isoformat(),
            'fecha_hasta': _dias(3).isoformat(),
            'hora_inicio': '14:00:00',
            'hora_fin': '17:00:00',
        })
        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_el_evento_no_lleva_datos_personales_ni_texto_libre(
        self, dueno, complejo, cliente_de, django_capture_on_commit_callbacks,
    ):
        datos = _dia_completo(complejo, descripcion='Aviso de Teodoro Arrúa')
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                cliente_de(dueno).post(URL, datos, format='json')

        _, evento = publicar.call_args.args
        assert set(evento) == {'event', 'cancha_id', 'fecha_desde', 'fecha_hasta', 'hora_inicio', 'hora_fin'}
        assert evento['cancha_id'] is None and evento['hora_inicio'] is None
        assert 'Teodoro' not in str(evento)

    def test_la_baja_tambien_se_anuncia(
        self, dueno, complejo, crear_excepcion, cliente_de, django_capture_on_commit_callbacks,
    ):
        excepcion = crear_excepcion(complejo)
        with mock.patch.object(DifusionGrillaService, 'publicar') as publicar:
            with django_capture_on_commit_callbacks(execute=True):
                cliente_de(dueno).delete(f'{URL}{excepcion.id}/')

        publicar.assert_called_once()
        assert publicar.call_args.args[0] == complejo.id

    def test_un_alta_rechazada_no_se_anuncia(self, dueno, complejo, cliente_de, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks() as pendientes:
            cliente_de(dueno).post(URL, _dia_completo(complejo, fecha_inicio=_dias(-1).isoformat()), format='json')

        assert pendientes == []

    def test_sin_grillas_suscriptas_la_publicacion_no_falla(self, dueno, complejo, cliente_de,
                                                            django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = cliente_de(dueno).post(URL, _dia_completo(complejo), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
