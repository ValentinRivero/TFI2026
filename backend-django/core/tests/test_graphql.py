from datetime import timedelta

import pytest
from django.test import Client
from rest_framework import status
from rest_framework.test import APIClient

from core.models import EstadoContrato, Servicio
from core.serializers_auth import TokenConRolSerializer

URL = '/graphql/'
URL_REST = '/api/complejos/'

CATALOGO = '''
query Catalogo($deporte: Int, $cobertura: Int, $servicio: [Int], $search: String, $ordering: String, $page: Int) {
  catalogoComplejos(
    deporte: $deporte, cobertura: $cobertura, servicio: $servicio, search: $search, ordering: $ordering, page: $page
  ) {
    count
    results {
      id nombre direccion latitud longitud telefonoContacto horasLimiteCancelacion infoSena precioDesde
      servicios { id nombre }
      deportes { id nombre }
    }
  }
}
'''


def _consultar(cliente, consulta=CATALOGO, **variables):
    return cliente.post(URL, {'query': consulta, 'variables': variables}, format='json')


def _con_token(token):
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return api


@pytest.fixture
def catalogo(dueno, otro_dueno, crear_complejo, crear_cancha, ofrecer_servicios):
    """Tres complejos públicos con deportes, coberturas y servicios distintos, y uno suspendido."""
    from core.models import Cobertura

    timbos = crear_complejo(dueno, 'Los Timbós', direccion='Pasaje Ñandubay 1540, Goya')
    crear_cancha(timbos, 'Pádel 1', deporte='Pádel', cobertura=Cobertura.TECHADA, precio_base='30000.00')
    ofrecer_servicios(timbos, 'Estacionamiento', 'Vestuarios')

    ceibo = crear_complejo(otro_dueno, 'El Ceibo')
    crear_cancha(ceibo, 'F5 1', precio_base='45000.00')
    crear_cancha(ceibo, 'Pádel 1', deporte='Pádel', precio_base='28000.00')
    ofrecer_servicios(ceibo, 'Estacionamiento')

    ruta = crear_complejo(otro_dueno, 'Ruta 12 Fútbol')
    crear_cancha(ruta, 'F5 1', precio_base='40000.00')

    crear_complejo(dueno, 'Complejo Suspendido', estado_contrato=EstadoContrato.SUSPENDIDO)
    return {'timbos': timbos, 'ceibo': ceibo, 'ruta': ruta}


def _rest(parametros):
    respuesta = APIClient().get(URL_REST, parametros)
    assert respuesta.status_code == status.HTTP_200_OK
    return respuesta.json()


@pytest.mark.django_db
class TestCatalogoComplejos:
    def test_es_publico_y_devuelve_la_primera_pagina(self, cliente, catalogo):
        respuesta = _consultar(cliente)

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert 'errors' not in cuerpo
        assert cuerpo['data']['catalogoComplejos']['count'] == 3

    def test_no_muestra_complejos_sin_contrato_activo(self, cliente, catalogo):
        nombres = [c['nombre'] for c in _consultar(cliente).json()['data']['catalogoComplejos']['results']]

        assert 'Complejo Suspendido' not in nombres

    @pytest.mark.parametrize('parametros', [
        {},
        {'ordering': '-nombre'},
        {'ordering': 'precio_desde'},
        {'search': 'timbos'},
        {'search': 'NANDUBAY'},
        {'cobertura': 2},
        {'servicio': ['Estacionamiento']},
        {'servicio': ['Estacionamiento', 'Vestuarios']},
        {'deporte': 'Pádel', 'ordering': '-precio_desde'},
    ])
    def test_devuelve_lo_mismo_que_la_api_rest(self, cliente, catalogo, parametros):
        from core.models import Deporte

        if 'deporte' in parametros:
            parametros['deporte'] = Deporte.objects.get(nombre=parametros['deporte']).id
        if 'servicio' in parametros:
            parametros['servicio'] = [Servicio.objects.get(nombre=nombre).id for nombre in parametros['servicio']]

        rest = _rest(parametros)
        graphql = _consultar(cliente, **parametros).json()['data']['catalogoComplejos']

        assert graphql['count'] == rest['count']
        assert [_a_rest(complejo) for complejo in graphql['results']] == rest['results']

    def test_no_expone_datos_del_propietario(self, cliente, catalogo):
        consulta = '{ catalogoComplejos { results { id propietario { email } } } }'

        respuesta = _consultar(cliente, consulta)

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'propietario' in respuesta.json()['errors'][0]['message']

    def test_pagina_de_a_veinte_como_rest(self, cliente, dueno, crear_complejo):
        for numero in range(21):
            crear_complejo(dueno, f'Complejo {numero:02d}')

        primera = _consultar(cliente).json()['data']['catalogoComplejos']
        segunda = _consultar(cliente, page=2).json()['data']['catalogoComplejos']

        assert (primera['count'], len(primera['results']), len(segunda['results'])) == (21, 20, 1)

    @pytest.mark.parametrize('variables,codigo', [
        ({'deporte': 999999}, 400),
        ({'cobertura': 9}, 400),
        ({'servicio': [999999]}, 400),
        ({'page': 7}, 404),
    ])
    def test_un_filtro_invalido_responde_con_errores_y_codigo(self, cliente, catalogo, variables, codigo):
        respuesta = _consultar(cliente, **variables)

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert cuerpo['data'] == {'catalogoComplejos': None}
        assert cuerpo['errors'][0]['extensions']['codigo'] == codigo
        assert cuerpo['errors'][0]['path'] == ['catalogoComplejos']


def _a_rest(complejo):
    """Pasa los nombres de campo de GraphQL (camelCase) a los de REST para comparar respuestas."""
    equivalencias = {
        'telefonoContacto': 'telefono_contacto',
        'horasLimiteCancelacion': 'horas_limite_cancelacion',
        'infoSena': 'info_sena',
        'precioDesde': 'precio_desde',
    }
    return {equivalencias.get(clave, clave): valor for clave, valor in complejo.items()}


@pytest.mark.django_db
class TestAutenticacionDeGraphQL:
    def test_con_token_valido_responde_igual(self, jugador, catalogo, cliente_de):
        assert 'errors' not in _consultar(cliente_de(jugador)).json()

    def test_el_catalogo_ignora_un_token_invalido_como_en_rest(self, catalogo):
        respuesta = _consultar(_con_token('no-es-un-jwt'))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['data']['catalogoComplejos']['count'] == 3

    def test_el_catalogo_ignora_un_token_vencido_como_en_rest(self, jugador, catalogo):
        token = TokenConRolSerializer.get_token(jugador).access_token
        token.set_exp(lifetime=-timedelta(minutes=1))

        respuesta = _consultar(_con_token(str(token)))

        assert respuesta.status_code == status.HTTP_200_OK
        assert 'errors' not in respuesta.json()

    def test_no_exige_csrf_porque_no_usa_cookies_de_sesion(self, catalogo):
        navegador = Client(enforce_csrf_checks=True)

        respuesta = navegador.post(URL, {'query': CATALOGO}, content_type='application/json')

        assert respuesta.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTransporteDeGraphQL:
    def test_get_no_se_admite_fuera_de_desarrollo(self, cliente, catalogo):
        respuesta = cliente.get(URL, {'query': '{ catalogoComplejos { count } }'})

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_graphiql_solo_con_debug(self, cliente, settings, catalogo):
        assert cliente.get(URL, HTTP_ACCEPT='text/html').status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        settings.DEBUG = True
        respuesta = cliente.get(URL, HTTP_ACCEPT='text/html')

        assert respuesta.status_code == status.HTTP_200_OK
        assert 'graphiql' in respuesta.content.decode().lower()

    def test_sin_consulta_responde_400(self, cliente):
        respuesta = cliente.post(URL, {}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['errors']

    def test_un_error_inesperado_no_filtra_detalles_internos(self, cliente, catalogo, monkeypatch):
        from core.services import CatalogoService

        def _falla():
            raise RuntimeError('conexion a 10.0.0.5 rechazada')

        monkeypatch.setattr(CatalogoService, 'complejos_publicos', staticmethod(_falla))

        respuesta = _consultar(cliente)

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.content.decode()
        assert '10.0.0.5' not in cuerpo
        assert respuesta.json()['errors'][0]['message'] == 'Error interno del servidor.'
