"""Marcadores del mapa del catálogo: colección liviana, pública, sin paginar y con los filtros del catálogo."""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from core.models import Cobertura, Complejo, Deporte, EstadoCancha, EstadoContrato, Servicio

URL = '/api/complejos/marcadores/'
TOKEN_INVALIDO = 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c3VhcmlvX2lkIjoiMSJ9.firma-invalida'
CAMPOS = {'id', 'nombre', 'latitud', 'longitud', 'precio_desde'}


def _ids(respuesta):
    return [marcador['id'] for marcador in respuesta.json()]


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
    ofrecer_servicios(timbos, 'Vestuarios')

    return SimpleNamespace(yacare=yacare, costa=costa, timbos=timbos)


class TestAccesoYFormato:
    def test_es_publico_y_devuelve_una_lista_sin_paginar(self, cliente, catalogo):
        respuesta = cliente.get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert isinstance(respuesta.json(), list)
        assert len(respuesta.json()) == 3

    def test_ignora_un_token_invalido(self, cliente, catalogo):
        cliente.credentials(HTTP_AUTHORIZATION=TOKEN_INVALIDO)

        assert cliente.get(URL).status_code == status.HTTP_200_OK

    def test_solo_admite_lectura(self, cliente, catalogo):
        # Una escritura sin sesión se corta antes por la autenticación, igual que en el resto de las rutas del catálogo.
        respuesta = cliente.post(URL, {'nombre': 'Complejo Falso'}, format='json')

        assert respuesta.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_405_METHOD_NOT_ALLOWED)
        assert not Complejo.objects.filter(nombre='Complejo Falso').exists()

    def test_lleva_solo_lo_que_dibuja_el_marcador(self, cliente, catalogo):
        marcador = next(m for m in cliente.get(URL).json() if m['id'] == catalogo.yacare.id)

        assert set(marcador) == CAMPOS
        assert marcador['nombre'] == 'El Yacaré'
        assert Decimal(marcador['latitud']) == Decimal('-29.14')
        assert Decimal(marcador['longitud']) == Decimal('-59.26')

    def test_no_expone_propietario_ni_contacto(self, cliente, catalogo):
        cuerpo = cliente.get(URL).content.decode()

        assert 'dueno@talibre.test' not in cuerpo
        assert 'propietario' not in cuerpo
        assert 'telefono' not in cuerpo

    def test_no_se_confunde_con_el_detalle_de_un_complejo(self, cliente, catalogo):
        assert cliente.get(f'/api/complejos/{catalogo.costa.id}/').json()['id'] == catalogo.costa.id
        assert isinstance(cliente.get(URL).json(), list)

    def test_se_ordena_por_nombre(self, cliente, catalogo):
        nombres = [marcador['nombre'] for marcador in cliente.get(URL).json()]

        assert nombres == sorted(nombres)


class TestPrecioDesde:
    def test_es_el_precio_minimo_de_las_canchas_activas(self, cliente, catalogo):
        precios = {m['id']: m['precio_desde'] for m in cliente.get(URL).json()}

        assert Decimal(precios[catalogo.yacare.id]) == Decimal('38000')
        assert Decimal(precios[catalogo.costa.id]) == Decimal('30000')

    def test_ignora_las_canchas_que_no_estan_activas(self, cliente, catalogo):
        catalogo.yacare.canchas.filter(nombre='Cancha 1').update(estado=EstadoCancha.EN_MANTENIMIENTO)

        precios = {m['id']: m['precio_desde'] for m in cliente.get(URL).json()}

        assert Decimal(precios[catalogo.yacare.id]) == Decimal('42000')

    def test_es_nulo_si_no_tiene_canchas_activas(self, cliente, dueno, crear_complejo):
        vacio = crear_complejo(dueno, 'Complejo Nuevo')

        marcador = next(m for m in cliente.get(URL).json() if m['id'] == vacio.id)

        assert marcador['precio_desde'] is None


class TestVisibilidad:
    @pytest.mark.parametrize('estado_contrato', [
        EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO, EstadoContrato.BAJA,
    ])
    def test_solo_muestra_contratos_activos(self, cliente, catalogo, dueno, crear_complejo, estado_contrato):
        oculto = crear_complejo(dueno, 'Complejo Oculto', estado_contrato=estado_contrato)

        assert oculto.id not in _ids(cliente.get(URL))

    def test_oculta_complejos_con_baja_logica(self, cliente, catalogo):
        catalogo.costa.desactivar()

        assert catalogo.costa.id not in _ids(cliente.get(URL))

    def test_un_contrato_suspendido_desaparece_al_instante(self, cliente, catalogo):
        assert catalogo.timbos.id in _ids(cliente.get(URL))

        catalogo.timbos.estado_contrato = EstadoContrato.SUSPENDIDO
        catalogo.timbos.save(update_fields=['estado_contrato', 'fecha_modificacion'])

        assert catalogo.timbos.id not in _ids(cliente.get(URL))


class TestFiltrosDelCatalogo:
    def test_filtra_por_deporte(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'deporte': Deporte.objects.get(nombre='Pádel').id})

        assert sorted(_ids(respuesta)) == sorted([catalogo.costa.id, catalogo.timbos.id])

    def test_filtra_por_cobertura(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'cobertura': Cobertura.TECHADA})

        assert sorted(_ids(respuesta)) == sorted([catalogo.yacare.id, catalogo.costa.id])

    def test_deporte_y_cobertura_se_exigen_sobre_la_misma_cancha(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'deporte': Deporte.objects.get(nombre='Pádel').id, 'cobertura': Cobertura.TECHADA})

        assert _ids(respuesta) == [catalogo.costa.id]

    def test_exige_todos_los_servicios_pedidos(self, cliente, catalogo):
        estacionamiento = Servicio.objects.get(nombre='Estacionamiento').id
        vestuarios = Servicio.objects.get(nombre='Vestuarios').id

        respuesta = cliente.get(f'{URL}?servicio={estacionamiento}&servicio={vestuarios}')

        assert _ids(respuesta) == [catalogo.yacare.id]

    def test_busca_por_nombre_sin_distinguir_tildes(self, cliente, catalogo):
        assert _ids(cliente.get(URL, {'search': 'timbos'})) == [catalogo.timbos.id]

    def test_ordena_por_precio_desde(self, cliente, catalogo):
        ascendente = _ids(cliente.get(URL, {'ordering': 'precio_desde'}))
        descendente = _ids(cliente.get(URL, {'ordering': '-precio_desde'}))

        assert ascendente == [catalogo.timbos.id, catalogo.costa.id, catalogo.yacare.id]
        assert descendente == ascendente[::-1]

    @pytest.mark.parametrize('parametros', [{'deporte': 99999}, {'cobertura': 9}, {'servicio': 99999}])
    def test_un_filtro_invalido_responde_400(self, cliente, catalogo, parametros):
        respuesta = cliente.get(URL, parametros)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['error'] is True


class TestColeccionAcotada:
    def test_devuelve_todos_los_complejos_aunque_superen_la_pagina_del_catalogo(self, cliente, dueno, crear_complejo):
        for numero in range(23):
            crear_complejo(dueno, f'Complejo {numero:02d}')

        assert len(cliente.get(URL).json()) == 23
        assert len(cliente.get('/api/complejos/').json()['results']) == 20

    def test_aplica_el_tope_configurado(self, cliente, dueno, crear_complejo, settings):
        settings.CATALOGO_MARCADORES_MAXIMO = 5
        for numero in range(8):
            crear_complejo(dueno, f'Complejo {numero:02d}')

        nombres = [marcador['nombre'] for marcador in cliente.get(URL).json()]

        assert nombres == [f'Complejo {numero:02d}' for numero in range(5)]

    def test_la_cantidad_de_consultas_no_depende_de_la_cantidad_de_complejos(
        self, cliente, dueno, crear_complejo, crear_cancha,
    ):
        def contar():
            with CaptureQueriesContext(connection) as contexto:
                assert cliente.get(URL).status_code == status.HTTP_200_OK
            return len(contexto)

        crear_cancha(crear_complejo(dueno, 'Complejo Base'), 'Cancha 1')
        con_uno = contar()
        for numero in range(5):
            crear_cancha(crear_complejo(dueno, f'Complejo {numero}'), 'Cancha 1')

        assert contar() == con_uno == 1
