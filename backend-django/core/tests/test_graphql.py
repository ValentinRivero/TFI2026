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
        error = respuesta.json()['errors'][0]
        assert (error['message'], error['extensions']['codigo']) == ('Error interno del servidor.', 500)

    def test_un_error_fuera_de_la_api_rest_tampoco_filtra_detalles(self, cliente, catalogo, monkeypatch):
        import core.schema

        def _falla(*args, **kwargs):
            raise RuntimeError('/srv/talibre/core/schema.py linea 40')

        monkeypatch.setattr(core.schema, 'listar_como_en_rest', _falla)

        respuesta = _consultar(cliente)

        assert '/srv/talibre' not in respuesta.content.decode()
        assert respuesta.json()['errors'][0]['message'] == 'Error interno del servidor.'


MIS_RESERVAS = '''
query MisReservas($estado: Int, $vigencia: String, $fechaDesde: String, $fechaHasta: String, $ordering: String, $page: Int) {
  misReservas(
    estado: $estado, vigencia: $vigencia, fechaDesde: $fechaDesde, fechaHasta: $fechaHasta,
    ordering: $ordering, page: $page
  ) {
    count
    results {
      id complejo { id nombre } cancha { id nombre } deporte fechaTurno horaInicio horaFin precioAcordado
      tipoOcupacion tipoOcupacionNombre estado estadoNombre cancelableHasta fechaCreacion
    }
  }
}
'''
URL_REST_MIAS = '/api/reservas/mias/'
EQUIVALENCIAS_RESERVA = {
    'fechaTurno': 'fecha_turno', 'horaInicio': 'hora_inicio', 'horaFin': 'hora_fin',
    'precioAcordado': 'precio_acordado', 'tipoOcupacion': 'tipo_ocupacion',
    'tipoOcupacionNombre': 'tipo_ocupacion_nombre', 'estadoNombre': 'estado_nombre',
    'cancelableHasta': 'cancelable_hasta', 'fechaCreacion': 'fecha_creacion',
}


@pytest.fixture
def reservas_del_jugador(jugador, crear_usuario, complejo, crear_cancha, crear_reserva):
    from datetime import date, time

    from core.models import EstadoReserva

    cancha = crear_cancha(complejo, 'Cancha 1')
    otro = crear_usuario('otro.jugador@talibre.test')
    propias = [
        crear_reserva(cancha, date(2026, 11, 10), time(18), time(19), estado=EstadoReserva.COMPLETADA),
        crear_reserva(cancha, date(2026, 11, 20), time(20), time(21), estado=EstadoReserva.PENDIENTE),
        crear_reserva(cancha, date(2026, 11, 25), time(19), time(20), estado=EstadoReserva.CANCELADA_JUGADOR),
    ]
    crear_reserva(cancha, date(2026, 11, 20), time(18), time(19), usuario=otro, creado_por=otro)
    return propias


def _mis_reservas(cliente, **variables):
    return _consultar(cliente, MIS_RESERVAS, **variables)


def _error(respuesta):
    assert respuesta.status_code == status.HTTP_200_OK
    cuerpo = respuesta.json()
    assert cuerpo['data'] == {'misReservas': None}
    assert cuerpo['errors'][0]['path'] == ['misReservas']
    return cuerpo['errors'][0]


@pytest.mark.django_db
class TestMisReservas:
    def test_devuelve_solo_las_reservas_propias(self, jugador, reservas_del_jugador, cliente_de):
        datos = _mis_reservas(cliente_de(jugador)).json()['data']['misReservas']

        assert datos['count'] == 3
        assert {fila['id'] for fila in datos['results']} == {reserva.id for reserva in reservas_del_jugador}

    @pytest.mark.parametrize('variables,parametros', [
        ({}, {}),
        ({'estado': 1}, {'estado': 1}),
        ({'vigencia': 'proximas'}, {'vigencia': 'proximas'}),
        ({'vigencia': 'pasadas'}, {'vigencia': 'pasadas'}),
        ({'fechaDesde': '2026-11-15', 'fechaHasta': '2026-11-22'}, {'fecha_desde': '2026-11-15', 'fecha_hasta': '2026-11-22'}),
        ({'ordering': '-fecha_turno'}, {'ordering': '-fecha_turno'}),
    ])
    def test_devuelve_lo_mismo_que_la_api_rest(
        self, reloj, jugador, reservas_del_jugador, cliente_de, variables, parametros,
    ):
        api = cliente_de(jugador)
        rest = api.get(URL_REST_MIAS, parametros).json()

        graphql = _mis_reservas(api, **variables).json()['data']['misReservas']

        assert graphql['count'] == rest['count']
        assert [
            {EQUIVALENCIAS_RESERVA.get(clave, clave): valor for clave, valor in fila.items()}
            for fila in graphql['results']
        ] == rest['results']

    def test_sin_token_responde_401_como_rest(self, reservas_del_jugador, cliente):
        error = _error(_mis_reservas(cliente))

        assert error['extensions']['codigo'] == 401
        assert error['message'] == cliente.get(URL_REST_MIAS).json()['detail']

    def test_token_invalido_responde_401_como_rest(self, reservas_del_jugador):
        api = _con_token('no-es-un-jwt')

        error = _error(_mis_reservas(api))

        assert error['extensions']['codigo'] == 401
        assert error['message'] == api.get(URL_REST_MIAS).json()['detail']

    def test_la_sesion_de_django_no_autentica(self, jugador, reservas_del_jugador):
        navegador = Client()
        navegador.force_login(jugador)

        respuesta = navegador.post(URL, {'query': MIS_RESERVAS}, content_type='application/json')

        assert respuesta.json()['errors'][0]['extensions']['codigo'] == 401

    @pytest.mark.parametrize('rol', ['dueno', 'operador'])
    def test_el_personal_del_complejo_recibe_403_auditado(self, request, rol, reservas_del_jugador, cliente_de):
        from core.models import LogAuditoria, TipoEventoAuditoria

        usuario = request.getfixturevalue(rol)

        error = _error(_mis_reservas(cliente_de(usuario)))

        assert error['extensions']['codigo'] == 403
        assert LogAuditoria.objects.filter(
            usuario=usuario, tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO,
        ).exists()

    def test_un_filtro_invalido_responde_400_con_el_detalle(self, jugador, reservas_del_jugador, cliente_de):
        error = _error(_mis_reservas(cliente_de(jugador), estado=9, fechaDesde='16/11/2026'))

        assert error['extensions']['codigo'] == 400
        assert set(error['extensions']['detalle']) == {'estado', 'fecha_desde'}

    def test_no_expone_las_observaciones_internas_del_complejo(self, jugador, reservas_del_jugador, cliente_de):
        respuesta = _consultar(cliente_de(jugador), '{ misReservas { results { id observaciones } } }')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'observaciones' in respuesta.json()['errors'][0]['message']

    def test_catalogo_y_reservas_en_una_misma_consulta(self, jugador, reservas_del_jugador, cliente_de):
        consulta = '{ catalogoComplejos { count } misReservas { count } }'

        datos = _consultar(cliente_de(jugador), consulta).json()['data']

        assert (datos['catalogoComplejos']['count'], datos['misReservas']['count']) == (1, 3)

    def test_un_anonimo_ve_el_catalogo_aunque_falle_misreservas(self, reservas_del_jugador, cliente):
        consulta = '{ catalogoComplejos { count } misReservas { count } }'

        cuerpo = _consultar(cliente, consulta).json()

        assert cuerpo['data'] == {'catalogoComplejos': {'count': 1}, 'misReservas': None}
        assert cuerpo['errors'][0]['extensions']['codigo'] == 401
