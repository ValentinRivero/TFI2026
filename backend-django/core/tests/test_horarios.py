from datetime import time
from decimal import Decimal
from unittest import mock

import pytest
from rest_framework import status

from core.models import DiaSemana, EstadoRegistro, HorarioApertura, RolPermiso
from core.repositories import CanchaRepository

URL = '/api/horarios/'


@pytest.fixture
def cancha(complejo, crear_cancha):
    return crear_cancha(complejo, 'Cancha Propia')


@pytest.fixture
def cancha_ajena(complejo_ajeno, crear_cancha):
    return crear_cancha(complejo_ajeno, 'Cancha Ajena')


@pytest.fixture
def horario_lunes(cancha):
    return HorarioApertura.objects.create(
        cancha=cancha, dia_semana=DiaSemana.LUNES, hora_apertura=time(14, 0), hora_cierre=time(23, 0),
    )


def _datos(cancha, **cambios):
    datos = {'cancha': cancha.id, 'dia_semana': DiaSemana.MARTES, 'hora_apertura': '14:00', 'hora_cierre': '23:00'}
    datos.update(cambios)
    return datos


def _quitar_permiso_de_precios():
    RolPermiso.objects.get(rol__nombre='DUENO_COMPLEJO', permiso__codigo='administrar_precios').desactivar()


class TestConsultaDeHorarios:
    def test_dueno_lista_los_horarios_de_su_cancha(self, dueno, cancha, horario_lunes, cliente_de):
        respuesta = cliente_de(dueno).get(URL, {'cancha': cancha.id})

        assert respuesta.status_code == status.HTTP_200_OK
        (horario,) = respuesta.json()['results']
        assert horario['dia_semana_nombre'] == 'Lunes'
        assert horario['hora_apertura'] == '14:00:00'
        assert horario['precio_diferenciado'] is None

    def test_operador_consulta_horarios(self, operador, horario_lunes, cliente_de):
        assert cliente_de(operador).get(URL).json()['count'] == 1

    def test_no_lista_horarios_dados_de_baja(self, dueno, horario_lunes, cliente_de):
        horario_lunes.desactivar()

        assert cliente_de(dueno).get(URL).json()['count'] == 0

    def test_consultar_una_cancha_ajena_responde_404(self, dueno, cancha_ajena, cliente_de):
        assert cliente_de(dueno).get(URL, {'cancha': cancha_ajena.id}).status_code == status.HTTP_404_NOT_FOUND

    def test_horario_ajeno_responde_404(self, dueno, cancha_ajena, cliente_de):
        ajeno = HorarioApertura.objects.create(
            cancha=cancha_ajena, dia_semana=0, hora_apertura=time(8, 0), hora_cierre=time(12, 0),
        )

        assert cliente_de(dueno).get(f'{URL}{ajeno.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_filtra_por_dia(self, dueno, cancha, horario_lunes, cliente_de):
        HorarioApertura.objects.create(cancha=cancha, dia_semana=2, hora_apertura=time(9, 0), hora_cierre=time(12, 0))

        resultados = cliente_de(dueno).get(URL, {'dia_semana': DiaSemana.LUNES}).json()['results']

        assert [item['id'] for item in resultados] == [horario_lunes.id]

    def test_dia_invalido_responde_400(self, dueno, cliente_de):
        assert cliente_de(dueno).get(URL, {'dia_semana': 7}).status_code == status.HTTP_400_BAD_REQUEST

    def test_jugador_recibe_403(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN


class TestAltaDeHorarios:
    def test_dueno_crea_un_horario(self, dueno, cancha, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos(cancha), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        horario = HorarioApertura.objects.get(id=respuesta.json()['id'])
        assert horario.hora_cierre == time(23, 0)
        assert horario.precio_diferenciado is None

    @pytest.mark.parametrize('apertura, cierre', [('20:00', '18:00'), ('18:00', '18:00')])
    def test_el_cierre_debe_ser_posterior_a_la_apertura(self, dueno, cancha, cliente_de, apertura, cierre):
        respuesta = cliente_de(dueno).post(
            URL, _datos(cancha, hora_apertura=apertura, hora_cierre=cierre), format='json',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_cierre' in respuesta.json()['detail']

    def test_rechaza_un_rango_solapado_el_mismo_dia(self, dueno, cancha, horario_lunes, cliente_de):
        respuesta = cliente_de(dueno).post(
            URL, _datos(cancha, dia_semana=DiaSemana.LUNES, hora_apertura='20:00', hora_cierre='23:30'), format='json',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'se solapa' in respuesta.json()['detail']['hora_apertura']
        assert HorarioApertura.objects.filter(cancha=cancha).count() == 1

    def test_un_dia_admite_cortes_con_precio_propio(self, dueno, cancha, horario_lunes, cliente_de):
        horario_lunes.hora_cierre = time(12, 0)
        horario_lunes.hora_apertura = time(8, 0)
        horario_lunes.save()

        respuesta = cliente_de(dueno).post(URL, _datos(
            cancha, dia_semana=DiaSemana.LUNES, hora_apertura='16:00', hora_cierre='23:00', precio_diferenciado='45000',
        ), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        rangos = cliente_de(dueno).get(URL, {'cancha': cancha.id, 'dia_semana': DiaSemana.LUNES}).json()['results']
        assert [(r['hora_apertura'], r['hora_cierre'], r['precio_diferenciado']) for r in rangos] == [
            ('08:00:00', '12:00:00', None), ('16:00:00', '23:00:00', '45000.00'),
        ]

    def test_los_rangos_contiguos_no_se_solapan(self, dueno, cancha, horario_lunes, cliente_de):
        respuesta = cliente_de(dueno).post(
            URL, _datos(cancha, dia_semana=DiaSemana.LUNES, hora_apertura='09:00', hora_cierre='14:00'), format='json',
        )

        assert respuesta.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize('apertura, cierre', [('10:00', '15:00'), ('22:00', '23:59'), ('15:00', '16:00')])
    def test_cualquier_superposicion_con_otro_rango_se_rechaza(
        self, dueno, cancha, horario_lunes, cliente_de, apertura, cierre,
    ):
        respuesta = cliente_de(dueno).post(
            URL, _datos(cancha, dia_semana=DiaSemana.LUNES, hora_apertura=apertura, hora_cierre=cierre), format='json',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert '14:00 a 23:00' in respuesta.json()['detail']['hora_apertura']

    def test_otro_dia_o_otra_cancha_no_se_solapan(self, dueno, complejo, cancha, horario_lunes, crear_cancha, cliente_de):
        otra = crear_cancha(complejo, 'Cancha 2')
        cliente = cliente_de(dueno)

        assert cliente.post(URL, _datos(cancha), format='json').status_code == status.HTTP_201_CREATED
        assert cliente.post(URL, _datos(otra, dia_semana=DiaSemana.LUNES), format='json').status_code == status.HTTP_201_CREATED

    def test_tras_la_baja_del_horario_el_dia_queda_libre(self, dueno, cancha, horario_lunes, cliente_de):
        horario_lunes.desactivar()

        respuesta = cliente_de(dueno).post(URL, _datos(cancha, dia_semana=DiaSemana.LUNES), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_precio_diferenciado_exige_administrar_precios(self, dueno, cancha, cliente_de):
        _quitar_permiso_de_precios()
        cliente = cliente_de(dueno)

        con_precio = cliente.post(URL, _datos(cancha, precio_diferenciado='42000'), format='json')
        sin_precio = cliente.post(URL, _datos(cancha), format='json')

        assert con_precio.status_code == status.HTTP_403_FORBIDDEN
        assert sin_precio.status_code == status.HTTP_201_CREATED

    def test_precio_negativo_responde_400(self, dueno, cancha, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos(cancha, precio_diferenciado='-5'), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_operador_no_crea_horarios(self, operador, cancha, cliente_de):
        assert cliente_de(operador).post(URL, _datos(cancha), format='json').status_code == status.HTTP_403_FORBIDDEN

    def test_cancha_ajena_responde_403(self, dueno, cancha_ajena, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos(cancha_ajena), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not HorarioApertura.objects.exists()

    def test_cancha_dada_de_baja_responde_400(self, dueno, cancha, cliente_de):
        cancha.desactivar()

        assert cliente_de(dueno).post(URL, _datos(cancha), format='json').status_code == status.HTTP_400_BAD_REQUEST

    def test_superadmin_crea_en_cualquier_cancha(self, superadmin, cancha_ajena, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, _datos(cancha_ajena, precio_diferenciado='30000'), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED


class TestEdicionDeHorarios:
    def _patch(self, cliente, horario, cuerpo):
        return cliente.patch(f'{URL}{horario.id}/', cuerpo, format='json')

    def test_amplia_el_rango_sin_chocar_consigo_mismo(self, dueno, horario_lunes, cliente_de):
        respuesta = self._patch(cliente_de(dueno), horario_lunes, {'hora_apertura': '09:00'})

        assert respuesta.status_code == status.HTTP_200_OK
        horario_lunes.refresh_from_db()
        assert horario_lunes.hora_apertura == time(9, 0)

    def test_valida_el_rango_contra_los_valores_vigentes(self, dueno, horario_lunes, cliente_de):
        respuesta = self._patch(cliente_de(dueno), horario_lunes, {'hora_cierre': '13:00'})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'hora_cierre' in respuesta.json()['detail']

    def test_mover_a_un_dia_con_un_rango_superpuesto_responde_400(self, dueno, cancha, horario_lunes, cliente_de):
        HorarioApertura.objects.create(
            cancha=cancha, dia_semana=DiaSemana.MARTES, hora_apertura=time(16, 0), hora_cierre=time(22, 0),
        )

        respuesta = self._patch(cliente_de(dueno), horario_lunes, {'dia_semana': DiaSemana.MARTES})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        horario_lunes.refresh_from_db()
        assert horario_lunes.dia_semana == DiaSemana.LUNES

    def test_extender_un_corte_sobre_el_siguiente_responde_400(self, dueno, cancha, cliente_de):
        manana = HorarioApertura.objects.create(
            cancha=cancha, dia_semana=DiaSemana.LUNES, hora_apertura=time(8, 0), hora_cierre=time(12, 0),
        )
        HorarioApertura.objects.create(
            cancha=cancha, dia_semana=DiaSemana.LUNES, hora_apertura=time(16, 0), hora_cierre=time(23, 0),
        )
        cliente = cliente_de(dueno)

        rechazo = self._patch(cliente, manana, {'hora_cierre': '17:00'})
        hasta_el_borde = self._patch(cliente, manana, {'hora_cierre': '16:00'})

        assert rechazo.status_code == status.HTTP_400_BAD_REQUEST
        assert hasta_el_borde.status_code == status.HTTP_200_OK

    def test_mover_a_un_dia_libre_esta_permitido(self, dueno, horario_lunes, cliente_de):
        assert self._patch(cliente_de(dueno), horario_lunes, {'dia_semana': DiaSemana.DOMINGO}).status_code == status.HTTP_200_OK

    def test_cambiar_el_precio_diferenciado_exige_administrar_precios(self, dueno, horario_lunes, cliente_de):
        _quitar_permiso_de_precios()
        cliente = cliente_de(dueno)

        cambio = self._patch(cliente, horario_lunes, {'precio_diferenciado': '50000'})
        mismo_valor = self._patch(cliente, horario_lunes, {'precio_diferenciado': None, 'hora_cierre': '22:00'})

        assert cambio.status_code == status.HTTP_403_FORBIDDEN
        assert mismo_valor.status_code == status.HTTP_200_OK
        horario_lunes.refresh_from_db()
        assert horario_lunes.precio_diferenciado is None

    def test_dueno_fija_y_quita_el_precio_diferenciado(self, dueno, horario_lunes, cliente_de):
        cliente = cliente_de(dueno)

        self._patch(cliente, horario_lunes, {'precio_diferenciado': '42000'})
        horario_lunes.refresh_from_db()
        assert horario_lunes.precio_diferenciado == Decimal('42000.00')

        self._patch(cliente, horario_lunes, {'precio_diferenciado': None})
        horario_lunes.refresh_from_db()
        assert horario_lunes.precio_diferenciado is None

    def test_la_cancha_no_se_puede_cambiar(self, dueno, complejo, cancha, horario_lunes, crear_cancha, cliente_de):
        otra = crear_cancha(complejo, 'Cancha 2')

        self._patch(cliente_de(dueno), horario_lunes, {'cancha': otra.id})

        horario_lunes.refresh_from_db()
        assert horario_lunes.cancha == cancha

    def test_operador_no_edita(self, operador, horario_lunes, cliente_de):
        assert self._patch(cliente_de(operador), horario_lunes, {'hora_cierre': '22:00'}).status_code == status.HTTP_403_FORBIDDEN


class TestBajaLogicaDeHorarios:
    def test_la_baja_es_logica(self, dueno, horario_lunes, cliente_de):
        respuesta = cliente_de(dueno).delete(f'{URL}{horario_lunes.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        horario_lunes.refresh_from_db()
        assert horario_lunes.estado == EstadoRegistro.BAJA

    def test_operador_no_da_de_baja(self, operador, horario_lunes, cliente_de):
        assert cliente_de(operador).delete(f'{URL}{horario_lunes.id}/').status_code == status.HTTP_403_FORBIDDEN

    def test_superadmin_da_de_baja_cualquier_horario(self, superadmin, horario_lunes, cliente_de):
        assert cliente_de(superadmin).delete(f'{URL}{horario_lunes.id}/').status_code == status.HTTP_204_NO_CONTENT


class TestAltasSimultaneas:
    def test_la_validacion_se_hace_con_la_cancha_bloqueada(self, dueno, cancha, cliente_de):
        # En PostgreSQL el bloqueo de la fila de la cancha impide que dos rangos superpuestos se validen a la vez.
        original = CanchaRepository.bloquear
        with mock.patch.object(CanchaRepository, 'bloquear', side_effect=original) as bloqueo:
            cliente_de(dueno).post(URL, _datos(cancha), format='json')

        bloqueo.assert_called_once_with(cancha.id)
