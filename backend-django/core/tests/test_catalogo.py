from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from core.models import (
    Cobertura,
    ComplejoServicio,
    Deporte,
    EstadoCancha,
    EstadoContrato,
    Servicio,
)

URL = '/api/complejos/'
TOKEN_INVALIDO = 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c3VhcmlvX2lkIjoiMSJ9.firma-invalida'


def _ids(respuesta):
    return [complejo['id'] for complejo in respuesta.json()['results']]


def _deporte(nombre):
    return Deporte.objects.get(nombre=nombre).id


def _servicio(nombre):
    return Servicio.objects.get(nombre=nombre).id


@pytest.fixture
def catalogo(dueno, crear_complejo, crear_cancha, ofrecer_servicios):
    yacare = crear_complejo(dueno, 'El Yacaré', direccion='Av. del Ombú 1250, Goya')
    crear_cancha(yacare, 'Cancha 1', 'Fútbol 5', cobertura=Cobertura.DESCUBIERTA, precio_base=Decimal('38000'))
    crear_cancha(yacare, 'Cancha 2', 'Fútbol 5', cobertura=Cobertura.TECHADA, precio_base=Decimal('42000'))
    ofrecer_servicios(yacare, 'Estacionamiento', 'Vestuarios')

    costa = crear_complejo(dueno, 'Costa Pádel', direccion='Calle Mburucuyá 860, Goya')
    crear_cancha(costa, 'Pádel 1', 'Pádel', cobertura=Cobertura.TECHADA, precio_base=Decimal('30000'))
    ofrecer_servicios(costa, 'Estacionamiento', 'Wi-Fi')

    timbos = crear_complejo(dueno, 'Los Timbós', direccion='Pasaje Ñandubay 1540, Goya')
    crear_cancha(timbos, 'Pádel Exterior', 'Pádel', cobertura=Cobertura.DESCUBIERTA, precio_base=Decimal('25000'))
    crear_cancha(timbos, 'Estadio', 'Básquet', cobertura=Cobertura.TECHADA, precio_base=Decimal('45000'))
    ofrecer_servicios(timbos, 'Vestuarios')

    return SimpleNamespace(yacare=yacare, costa=costa, timbos=timbos)


class TestCatalogosMaestros:
    @pytest.mark.parametrize('ruta', ['/api/deportes/', '/api/servicios/'])
    def test_son_publicos_y_no_paginan(self, cliente, rbac, ruta):
        respuesta = cliente.get(ruta)

        assert respuesta.status_code == status.HTTP_200_OK
        assert isinstance(respuesta.json(), list)
        assert set(respuesta.json()[0]) == {'id', 'nombre'}

    @pytest.mark.parametrize('ruta', ['/api/deportes/', '/api/servicios/'])
    def test_ignoran_un_token_invalido(self, cliente, rbac, ruta):
        cliente.credentials(HTTP_AUTHORIZATION=TOKEN_INVALIDO)

        assert cliente.get(ruta).status_code == status.HTTP_200_OK

    def test_deportes_lista_solo_los_activos_ordenados(self, cliente, rbac):
        Deporte.objects.get(nombre='Tenis').desactivar()

        nombres = [deporte['nombre'] for deporte in cliente.get('/api/deportes/').json()]

        assert 'Tenis' not in nombres
        assert nombres == sorted(nombres)

    def test_servicios_lista_solo_los_activos(self, cliente, rbac):
        Servicio.objects.get(nombre='Wi-Fi').desactivar()

        nombres = [servicio['nombre'] for servicio in cliente.get('/api/servicios/').json()]

        assert 'Wi-Fi' not in nombres
        assert 'Estacionamiento' in nombres

    def test_son_de_solo_lectura(self, cliente, rbac):
        respuesta = cliente.post('/api/deportes/', {'nombre': 'Hockey'}, format='json')

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestVisibilidadDelCatalogo:
    def test_es_publico_y_paginado(self, cliente, catalogo):
        respuesta = cliente.get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert set(respuesta.json()) == {'count', 'next', 'previous', 'results'}
        assert respuesta.json()['count'] == 3

    def test_ignora_un_token_invalido(self, cliente, catalogo):
        cliente.credentials(HTTP_AUTHORIZATION=TOKEN_INVALIDO)

        assert cliente.get(URL).status_code == status.HTTP_200_OK
        assert cliente.get(f'{URL}{catalogo.costa.id}/').status_code == status.HTTP_200_OK

    def test_pagina_de_a_20(self, cliente, dueno, crear_complejo):
        for numero in range(21):
            crear_complejo(dueno, f'Complejo {numero:02d}')

        primera = cliente.get(URL).json()
        segunda = cliente.get(URL, {'page': 2}).json()

        assert primera['count'] == 21
        assert len(primera['results']) == 20
        assert primera['next'] is not None
        assert len(segunda['results']) == 1

    @pytest.mark.parametrize('estado_contrato', [
        EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA,
    ])
    def test_solo_muestra_contratos_activos(self, cliente, catalogo, dueno, crear_complejo, estado_contrato):
        oculto = crear_complejo(dueno, 'Complejo Oculto', estado_contrato=estado_contrato)

        assert oculto.id not in _ids(cliente.get(URL))
        assert cliente.get(f'{URL}{oculto.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_oculta_complejos_con_baja_logica(self, cliente, catalogo):
        catalogo.costa.desactivar()

        assert catalogo.costa.id not in _ids(cliente.get(URL))
        assert cliente.get(f'{URL}{catalogo.costa.id}/').status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize('estado_contrato', [EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA])
    def test_suspender_o_dar_de_baja_el_contrato_oculta_al_instante(
        self, cliente, catalogo, superadmin, cliente_de, estado_contrato,
    ):
        assert catalogo.costa.id in _ids(cliente.get(URL))

        cliente_de(superadmin).patch(
            f'/api/contratos/{catalogo.costa.id}/', {'estado_contrato': estado_contrato}, format='json',
        )

        assert catalogo.costa.id not in _ids(cliente.get(URL))
        assert cliente.get(f'{URL}{catalogo.costa.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_el_404_de_un_contrato_inactivo_es_igual_al_de_un_inexistente(self, cliente, dueno, crear_complejo):
        pendiente = crear_complejo(dueno, 'Pendiente', estado_contrato=EstadoContrato.PENDIENTE)

        assert cliente.get(f'{URL}{pendiente.id}/').json() == cliente.get(f'{URL}999999/').json()

    def test_el_catalogo_no_admite_escritura_anonima(self, cliente, catalogo):
        respuesta = cliente.patch(f'{URL}{catalogo.costa.id}/', {'nombre': 'Hackeado'}, format='json')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED


class TestContenidoDelCatalogo:
    def test_el_listado_trae_coordenadas_servicios_deportes_y_precio_desde(self, cliente, catalogo):
        resultados = {complejo['nombre']: complejo for complejo in cliente.get(URL).json()['results']}
        yacare = resultados['El Yacaré']

        assert yacare['latitud'] == '-29.140000'
        assert yacare['longitud'] == '-59.260000'
        assert [servicio['nombre'] for servicio in yacare['servicios']] == ['Estacionamiento', 'Vestuarios']
        assert [deporte['nombre'] for deporte in yacare['deportes']] == ['Fútbol 5']
        assert yacare['precio_desde'] == '38000.00'
        assert 'canchas' not in yacare

    def test_no_expone_al_propietario_ni_datos_personales(self, cliente, catalogo, dueno):
        listado = cliente.get(URL).content.decode()
        detalle = cliente.get(f'{URL}{catalogo.yacare.id}/').content.decode()

        for cuerpo in (listado, detalle):
            assert dueno.email not in cuerpo
            assert dueno.nombre_completo not in cuerpo
            assert 'propietario' not in cuerpo

    def test_el_detalle_incluye_solo_las_canchas_activas(self, cliente, catalogo, crear_cancha):
        crear_cancha(catalogo.yacare, 'En Obra', estado=EstadoCancha.EN_MANTENIMIENTO)
        crear_cancha(catalogo.yacare, 'Vieja', estado=EstadoCancha.BAJA)

        detalle = cliente.get(f'{URL}{catalogo.yacare.id}/').json()

        assert [cancha['nombre'] for cancha in detalle['canchas']] == ['Cancha 1', 'Cancha 2']
        assert detalle['canchas'][1]['cobertura_nombre'] == 'Techada'
        assert detalle['canchas'][0]['deporte']['nombre'] == 'Fútbol 5'
        assert detalle['info_sena'] == ''
        assert detalle['horas_limite_cancelacion'] == 4

    def test_un_servicio_dado_de_baja_no_se_muestra(self, cliente, catalogo):
        ComplejoServicio.objects.get(complejo=catalogo.yacare, servicio__nombre='Vestuarios').desactivar()
        Servicio.objects.get(nombre='Estacionamiento').desactivar()

        detalle = cliente.get(f'{URL}{catalogo.yacare.id}/').json()

        assert detalle['servicios'] == []

    def test_precio_desde_ignora_canchas_no_activas(self, cliente, catalogo, crear_cancha):
        crear_cancha(catalogo.yacare, 'Barata en obra', estado=EstadoCancha.EN_MANTENIMIENTO, precio_base=Decimal('1'))

        assert cliente.get(f'{URL}{catalogo.yacare.id}/').json()['precio_desde'] == '38000.00'

    def test_un_complejo_sin_canchas_activas_informa_precio_nulo(self, cliente, dueno, crear_complejo):
        vacio = crear_complejo(dueno, 'Sin Canchas')

        detalle = cliente.get(f'{URL}{vacio.id}/').json()

        assert detalle['precio_desde'] is None
        assert detalle['canchas'] == []
        assert detalle['deportes'] == []


class TestSinConsultasNMasUno:
    def _consultas(self, cliente, ruta):
        with CaptureQueriesContext(connection) as contexto:
            assert cliente.get(ruta).status_code == status.HTTP_200_OK
        return len(contexto.captured_queries)

    def test_el_listado_no_crece_con_la_cantidad_de_complejos(
        self, cliente, dueno, crear_complejo, crear_cancha, ofrecer_servicios,
    ):
        def _poblar(cantidad, desde):
            for numero in range(desde, desde + cantidad):
                complejo = crear_complejo(dueno, f'Complejo {numero:02d}')
                crear_cancha(complejo, 'Cancha A', 'Fútbol 5')
                crear_cancha(complejo, 'Cancha B', 'Pádel')
                ofrecer_servicios(complejo, 'Wi-Fi', 'Buffet')

        _poblar(2, 0)
        con_pocos = self._consultas(cliente, URL)
        _poblar(10, 2)
        con_muchos = self._consultas(cliente, URL)

        assert con_pocos == con_muchos
        assert con_muchos <= 4

    def test_el_detalle_usa_una_cantidad_fija_de_consultas(self, cliente, catalogo):
        assert self._consultas(cliente, f'{URL}{catalogo.timbos.id}/') <= 3


class TestFiltrosDelCatalogo:
    def test_filtra_por_deporte(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'deporte': _deporte('Pádel')})

        assert set(_ids(respuesta)) == {catalogo.costa.id, catalogo.timbos.id}

    def test_filtra_por_cobertura(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'cobertura': Cobertura.DESCUBIERTA})

        assert set(_ids(respuesta)) == {catalogo.yacare.id, catalogo.timbos.id}

    def test_deporte_y_cobertura_se_exigen_sobre_la_misma_cancha(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'deporte': _deporte('Pádel'), 'cobertura': Cobertura.TECHADA})

        assert _ids(respuesta) == [catalogo.costa.id]

    def test_un_deporte_solo_en_canchas_no_activas_no_cuenta(self, cliente, catalogo, crear_cancha):
        crear_cancha(catalogo.yacare, 'Tenis en obra', 'Tenis', estado=EstadoCancha.EN_MANTENIMIENTO)

        assert _ids(cliente.get(URL, {'deporte': _deporte('Tenis')})) == []

    def test_filtra_por_un_servicio(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'servicio': _servicio('Vestuarios')})

        assert set(_ids(respuesta)) == {catalogo.yacare.id, catalogo.timbos.id}

    def test_varios_servicios_se_exigen_todos(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'servicio': [_servicio('Estacionamiento'), _servicio('Wi-Fi')]})

        assert _ids(respuesta) == [catalogo.costa.id]

    def test_un_servicio_dado_de_baja_en_el_complejo_no_cuenta(self, cliente, catalogo):
        ComplejoServicio.objects.get(complejo=catalogo.costa, servicio__nombre='Wi-Fi').desactivar()

        assert _ids(cliente.get(URL, {'servicio': _servicio('Wi-Fi')})) == []

    def test_busca_por_nombre_y_direccion(self, cliente, catalogo):
        assert _ids(cliente.get(URL, {'search': 'yacare'})) == [catalogo.yacare.id]
        assert _ids(cliente.get(URL, {'search': 'Mburucuyá'})) == [catalogo.costa.id]

    @pytest.mark.parametrize('termino', ['timbos', 'TIMBOS', 'Timbós', 'los timbós', 'NANDUBAY'])
    def test_la_busqueda_ignora_tildes_y_mayusculas(self, cliente, catalogo, termino):
        assert _ids(cliente.get(URL, {'search': termino})) == [catalogo.timbos.id]

    def test_un_termino_con_tilde_encuentra_texto_sin_tilde(self, cliente, catalogo):
        assert _ids(cliente.get(URL, {'search': 'Pádel'})) == [catalogo.costa.id]

    def test_varios_terminos_se_exigen_todos(self, cliente, catalogo):
        assert _ids(cliente.get(URL, {'search': 'goya ombu'})) == [catalogo.yacare.id]

    def test_filtros_combinados(self, cliente, catalogo):
        respuesta = cliente.get(URL, {
            'deporte': _deporte('Fútbol 5'),
            'cobertura': Cobertura.TECHADA,
            'servicio': _servicio('Estacionamiento'),
            'search': 'Ombú',
        })

        assert _ids(respuesta) == [catalogo.yacare.id]

    def test_filtros_combinados_sin_coincidencias_devuelven_lista_vacia(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'deporte': _deporte('Básquet'), 'servicio': _servicio('Wi-Fi')})

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['count'] == 0

    def test_orden_por_defecto_alfabetico(self, cliente, catalogo):
        assert _ids(cliente.get(URL)) == [catalogo.costa.id, catalogo.yacare.id, catalogo.timbos.id]

    def test_ordena_por_nombre_descendente(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'ordering': '-nombre'})

        assert _ids(respuesta) == [catalogo.timbos.id, catalogo.yacare.id, catalogo.costa.id]

    def test_ordena_por_precio_desde(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'ordering': 'precio_desde'})

        assert _ids(respuesta) == [catalogo.timbos.id, catalogo.costa.id, catalogo.yacare.id]

    def test_un_orden_fuera_de_la_lista_blanca_se_ignora(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'ordering': 'propietario__email'})

        assert respuesta.status_code == status.HTTP_200_OK
        assert _ids(respuesta) == [catalogo.costa.id, catalogo.yacare.id, catalogo.timbos.id]

    def test_un_parametro_no_declarado_se_ignora(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'propietario': 1, 'estado_contrato': EstadoContrato.PENDIENTE})

        assert respuesta.json()['count'] == 3

    @pytest.mark.parametrize('parametros', [
        {'deporte': 999999},
        {'deporte': 'futbol'},
        {'cobertura': 9},
        {'servicio': 'abc'},
        {'servicio': 999999},
    ])
    def test_valores_invalidos_responden_400(self, cliente, catalogo, parametros):
        respuesta = cliente.get(URL, parametros)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['error'] is True
        assert set(parametros) <= set(respuesta.json()['detail'])

    def test_un_deporte_dado_de_baja_no_es_filtrable(self, cliente, catalogo):
        Deporte.objects.get(nombre='Pádel').desactivar()

        assert cliente.get(URL, {'deporte': _deporte('Pádel')}).status_code == status.HTTP_400_BAD_REQUEST
