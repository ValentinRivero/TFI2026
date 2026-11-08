from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework import status

from core.models import (
    Cancha,
    Cobertura,
    Deporte,
    EstadoCancha,
    EstadoReserva,
    EstadoTurnoFijo,
    Iluminacion,
    Reserva,
    RolPermiso,
    TipoOcupacion,
    TipoSuperficie,
    TurnoFijo,
)
from core.repositories import CanchaRepository

URL = '/api/canchas/'


def _datos_alta(complejo, **cambios):
    datos = {
        'complejo': complejo.id,
        'deporte': Deporte.objects.get(nombre='Fútbol 5').id,
        'nombre': 'Cancha Nueva',
        'tipo_superficie': TipoSuperficie.CESPED_SINTETICO,
        'cobertura': Cobertura.TECHADA,
        'iluminacion': Iluminacion.LED,
        'duracion_turno_min': 90,
        'precio_base': '40000.00',
    }
    datos.update(cambios)
    return datos


def _quitar_permiso_de_precios():
    RolPermiso.objects.get(rol__nombre='DUENO_COMPLEJO', permiso__codigo='administrar_precios').desactivar()


@pytest.fixture
def cancha(complejo, crear_cancha):
    return crear_cancha(complejo, 'Cancha Propia')


@pytest.fixture
def cancha_ajena(complejo_ajeno, crear_cancha):
    return crear_cancha(complejo_ajeno, 'Cancha Ajena')


class TestConsultaDeCanchas:
    def test_dueno_lista_solo_las_suyas(self, dueno, cancha, cancha_ajena, cliente_de):
        respuesta = cliente_de(dueno).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert [item['id'] for item in respuesta.json()['results']] == [cancha.id]
        assert respuesta.json()['results'][0]['estado_nombre'] == 'Activa'

    def test_incluye_mantenimiento_y_excluye_bajas(self, dueno, complejo, cancha, crear_cancha, cliente_de):
        en_obra = crear_cancha(complejo, 'En Obra', estado=EstadoCancha.EN_MANTENIMIENTO)
        crear_cancha(complejo, 'Vieja', estado=EstadoCancha.BAJA)

        ids = {item['id'] for item in cliente_de(dueno).get(URL).json()['results']}

        assert ids == {cancha.id, en_obra.id}

    def test_filtra_por_complejo_y_estado(self, superadmin, cancha, cancha_ajena, complejo, cliente_de):
        cliente = cliente_de(superadmin)

        por_complejo = cliente.get(URL, {'complejo': complejo.id}).json()['results']
        en_obra = cliente.get(URL, {'estado': EstadoCancha.EN_MANTENIMIENTO}).json()['results']

        assert [item['id'] for item in por_complejo] == [cancha.id]
        assert en_obra == []

    def test_consultar_un_complejo_ajeno_responde_404(self, dueno, cancha_ajena, complejo_ajeno, cliente_de):
        respuesta = cliente_de(dueno).get(URL, {'complejo': complejo_ajeno.id})

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_operador_ve_las_canchas_de_su_complejo(self, operador, cancha, cancha_ajena, cliente_de):
        cliente = cliente_de(operador)

        assert [item['id'] for item in cliente.get(URL).json()['results']] == [cancha.id]
        assert cliente.get(f'{URL}{cancha_ajena.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_jugador_recibe_403(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN

    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED


class TestAltaDeCanchas:
    def test_dueno_da_de_alta_en_su_complejo(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo, nombre='<b>Cancha</b> Nueva'), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        cancha = Cancha.objects.get(id=respuesta.json()['id'])
        assert cancha.nombre == 'Cancha Nueva'
        assert cancha.complejo == complejo
        assert cancha.duracion_turno_min == 90
        assert cancha.estado == EstadoCancha.ACTIVA
        assert respuesta.json()['deporte_nombre'] == 'Fútbol 5'

    def test_nombre_repetido_en_el_complejo_responde_400(self, dueno, complejo, cancha, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo, nombre='cancha propia'), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'nombre' in respuesta.json()['detail']

    def test_el_nombre_de_una_cancha_dada_de_baja_se_puede_reutilizar(self, dueno, complejo, cancha, cliente_de):
        cancha.desactivar()

        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo, nombre='Cancha Propia'), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_el_mismo_nombre_en_otro_complejo_esta_permitido(self, superadmin, complejo_ajeno, cancha, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, _datos_alta(complejo_ajeno, nombre='Cancha Propia'), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_operador_no_da_de_alta(self, operador, complejo, cliente_de):
        assert cliente_de(operador).post(URL, _datos_alta(complejo), format='json').status_code == status.HTTP_403_FORBIDDEN

    def test_dueno_no_da_de_alta_en_complejo_ajeno(self, dueno, complejo_ajeno, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo_ajeno), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not Cancha.objects.filter(nombre='Cancha Nueva').exists()

    def test_superadmin_da_de_alta_en_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        assert cliente_de(superadmin).post(URL, _datos_alta(complejo_ajeno), format='json').status_code == status.HTTP_201_CREATED

    def test_el_alta_exige_administrar_precios(self, dueno, complejo, cliente_de):
        _quitar_permiso_de_precios()

        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert 'precio_base' in respuesta.json()['detail']
        assert not Cancha.objects.filter(nombre='Cancha Nueva').exists()

    @pytest.mark.parametrize('campo, valor', [
        ('precio_base', '-1'),
        ('duracion_turno_min', 45),
        ('tipo_superficie', 99),
        ('cobertura', 0),
        ('estado', EstadoCancha.BAJA),
        ('nombre', '<i></i>'),
    ])
    def test_datos_invalidos_responden_400(self, dueno, complejo, cliente_de, campo, valor):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo, **{campo: valor}), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert campo in respuesta.json()['detail']

    def test_deporte_dado_de_baja_responde_400(self, dueno, complejo, cliente_de):
        Deporte.objects.get(nombre='Fútbol 5').desactivar()

        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'deporte' in respuesta.json()['detail']

    def test_complejo_dado_de_baja_responde_400(self, superadmin, complejo, cliente_de):
        complejo.desactivar()

        respuesta = cliente_de(superadmin).post(URL, _datos_alta(complejo), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST


class TestEdicionDeCanchas:
    def _patch(self, cliente, cancha, cuerpo):
        return cliente.patch(f'{URL}{cancha.id}/', cuerpo, format='json')

    def test_dueno_edita_su_cancha(self, dueno, cancha, cliente_de):
        respuesta = self._patch(cliente_de(dueno), cancha, {
            'nombre': 'Cancha Central', 'iluminacion': Iluminacion.HALOGENA, 'precio_base': '45000',
        })

        assert respuesta.status_code == status.HTTP_200_OK
        cancha.refresh_from_db()
        assert cancha.nombre == 'Cancha Central'
        assert cancha.precio_base == Decimal('45000.00')

    def test_cambiar_el_precio_exige_administrar_precios(self, dueno, cancha, cliente_de):
        _quitar_permiso_de_precios()

        respuesta = self._patch(cliente_de(dueno), cancha, {'precio_base': '1.00', 'nombre': 'Otra'})

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        cancha.refresh_from_db()
        assert cancha.precio_base == Decimal('38000.00')
        assert cancha.nombre == 'Cancha Propia'

    def test_sin_administrar_precios_puede_editar_lo_demas(self, dueno, cancha, cliente_de):
        _quitar_permiso_de_precios()
        cliente = cliente_de(dueno)

        assert self._patch(cliente, cancha, {'nombre': 'Otra'}).status_code == status.HTTP_200_OK
        assert self._patch(cliente, cancha, {'precio_base': '38000'}).status_code == status.HTTP_200_OK

    def test_el_superadmin_hereda_administrar_precios(self, superadmin, cancha, cliente_de):
        RolPermiso.objects.get(rol__nombre='SUPERADMIN', permiso__codigo='administrar_precios').desactivar()

        assert self._patch(cliente_de(superadmin), cancha, {'precio_base': '50000'}).status_code == status.HTTP_200_OK

    def test_el_complejo_no_se_puede_cambiar(self, dueno, cancha, complejo, complejo_ajeno, cliente_de):
        self._patch(cliente_de(dueno), cancha, {'complejo': complejo_ajeno.id})

        cancha.refresh_from_db()
        assert cancha.complejo == complejo

    def test_pasar_a_mantenimiento_la_quita_del_catalogo(self, dueno, cancha, complejo, cliente, cliente_de):
        respuesta = self._patch(cliente_de(dueno), cancha, {'estado': EstadoCancha.EN_MANTENIMIENTO})

        assert respuesta.status_code == status.HTTP_200_OK
        assert cliente.get(f'/api/complejos/{complejo.id}/').json()['canchas'] == []

    def test_la_baja_no_se_hace_editando_el_estado(self, dueno, cancha, cliente_de):
        respuesta = self._patch(cliente_de(dueno), cancha, {'estado': EstadoCancha.BAJA})

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_renombrar_a_un_nombre_ocupado_responde_400(self, dueno, complejo, cancha, crear_cancha, cliente_de):
        crear_cancha(complejo, 'Cancha 2')

        assert self._patch(cliente_de(dueno), cancha, {'nombre': 'Cancha 2'}).status_code == status.HTTP_400_BAD_REQUEST

    def test_operador_no_edita(self, operador, cancha, cliente_de):
        assert self._patch(cliente_de(operador), cancha, {'nombre': 'X'}).status_code == status.HTTP_403_FORBIDDEN

    def test_cancha_ajena_responde_404(self, dueno, cancha_ajena, cliente_de):
        assert self._patch(cliente_de(dueno), cancha_ajena, {'nombre': 'X'}).status_code == status.HTTP_404_NOT_FOUND


class TestBajaLogicaDeCanchas:
    def _reservar(self, cancha, usuario, dias, estado=EstadoReserva.CONFIRMADA):
        return Reserva.objects.create(
            cancha=cancha, usuario=usuario, creado_por=usuario,
            fecha_turno=timezone.localdate() + timedelta(days=dias),
            hora_inicio=time(20, 0), hora_fin=time(21, 0), precio_acordado=Decimal('38000'),
            tipo_ocupacion=TipoOcupacion.WEB, estado=estado,
        )

    def test_la_baja_es_logica(self, dueno, cancha, cliente_de):
        respuesta = cliente_de(dueno).delete(f'{URL}{cancha.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        cancha.refresh_from_db()
        assert cancha.estado == EstadoCancha.BAJA
        assert cliente_de(dueno).get(f'{URL}{cancha.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_la_cancha_dada_de_baja_desaparece_del_catalogo(self, dueno, cancha, complejo, cliente, cliente_de):
        cliente_de(dueno).delete(f'{URL}{cancha.id}/')

        assert cliente.get(f'/api/complejos/{complejo.id}/').json()['canchas'] == []

    def test_con_reservas_futuras_activas_no_se_da_de_baja(self, dueno, jugador, cancha, cliente_de):
        self._reservar(cancha, jugador, dias=3)

        respuesta = cliente_de(dueno).delete(f'{URL}{cancha.id}/')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        cancha.refresh_from_db()
        assert cancha.estado == EstadoCancha.ACTIVA

    def test_con_turnos_fijos_vigentes_no_se_da_de_baja(self, dueno, cancha, cliente_de):
        TurnoFijo.objects.create(
            cancha=cancha, creado_por=dueno, nombre_cliente_manual='Los del Martes', dia_semana=1,
            hora_inicio=time(21, 0), hora_fin=time(22, 0), fecha_inicio_vigencia=timezone.localdate(),
        )

        assert cliente_de(dueno).delete(f'{URL}{cancha.id}/').status_code == status.HTTP_400_BAD_REQUEST

    def test_reservas_pasadas_canceladas_o_turnos_vencidos_no_impiden_la_baja(
        self, dueno, jugador, cancha, cliente_de,
    ):
        self._reservar(cancha, jugador, dias=-2)
        self._reservar(cancha, jugador, dias=5, estado=EstadoReserva.CANCELADA_JUGADOR)
        TurnoFijo.objects.create(
            cancha=cancha, creado_por=dueno, nombre_cliente_manual='Viejo', dia_semana=1,
            hora_inicio=time(21, 0), hora_fin=time(22, 0),
            fecha_inicio_vigencia=timezone.localdate() - timedelta(days=60),
            fecha_fin_vigencia=timezone.localdate() - timedelta(days=1),
        )
        TurnoFijo.objects.create(
            cancha=cancha, creado_por=dueno, nombre_cliente_manual='De baja', dia_semana=2,
            hora_inicio=time(21, 0), hora_fin=time(22, 0), fecha_inicio_vigencia=timezone.localdate(),
            estado=EstadoTurnoFijo.BAJA,
        )

        assert cliente_de(dueno).delete(f'{URL}{cancha.id}/').status_code == status.HTTP_204_NO_CONTENT

    def test_operador_no_da_de_baja(self, operador, cancha, cliente_de):
        assert cliente_de(operador).delete(f'{URL}{cancha.id}/').status_code == status.HTTP_403_FORBIDDEN

    def test_cancha_ajena_responde_404(self, dueno, cancha_ajena, cliente_de):
        assert cliente_de(dueno).delete(f'{URL}{cancha_ajena.id}/').status_code == status.HTTP_404_NOT_FOUND
        cancha_ajena.refresh_from_db()
        assert cancha_ajena.estado == EstadoCancha.ACTIVA

    def test_superadmin_da_de_baja_cualquier_cancha(self, superadmin, cancha_ajena, cliente_de):
        assert cliente_de(superadmin).delete(f'{URL}{cancha_ajena.id}/').status_code == status.HTTP_204_NO_CONTENT


class TestAltasSimultaneas:
    """
    Entre la validación previa y el INSERT otra petición puede ocupar el nombre: la restricción parcial
    uq_cancha_nombre_activa decide y la API responde 400, nunca 500.
    """

    def test_alta_concurrente_con_el_mismo_nombre(self, dueno, complejo, cancha, cliente_de):
        with mock.patch.object(CanchaRepository, 'existe_nombre', return_value=False):
            respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo, nombre='Cancha Propia'), format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'nombre' in respuesta.json()['detail']
        assert Cancha.objects.filter(complejo=complejo).count() == 1

    def test_renombrado_concurrente_al_mismo_nombre(self, dueno, complejo, cancha, crear_cancha, cliente_de):
        otra = crear_cancha(complejo, 'Cancha 2')

        with mock.patch.object(CanchaRepository, 'existe_nombre', return_value=False):
            respuesta = cliente_de(dueno).patch(f'{URL}{otra.id}/', {'nombre': 'Cancha Propia'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        otra.refresh_from_db()
        assert otra.nombre == 'Cancha 2'
