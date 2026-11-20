import pytest
from rest_framework import status

from core.models import (
    ComplejoServicio,
    Deporte,
    EstadoCancha,
    EstadoRegistro,
    EstadoUsuario,
    Rol,
    Servicio,
    Usuario,
)

DEPORTES = '/api/sistema/deportes/'
SERVICIOS = '/api/sistema/servicios/'
ROLES = '/api/sistema/roles/'


@pytest.fixture
def api(superadmin, cliente_de):
    return cliente_de(superadmin)


def _id(modelo, **filtro):
    return modelo.objects.get(**filtro).id


def _usos(api, ruta, registro_id):
    return api.get(f'{ruta}{registro_id}/usos/')


def _cantidad_listada(api, ruta, registro_id):
    return next(item['usos'] for item in api.get(ruta).json() if item['id'] == registro_id)


class TestAcceso:
    @pytest.mark.parametrize('ruta', [DEPORTES, SERVICIOS, ROLES])
    def test_anonimo_recibe_401(self, cliente, rbac, ruta):
        assert cliente.get(f'{ruta}1/usos/').status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno'])
    @pytest.mark.parametrize('ruta', [DEPORTES, SERVICIOS, ROLES])
    def test_roles_sin_permiso_reciben_403(self, request, cliente_de, ruta, fixture_usuario):
        api = cliente_de(request.getfixturevalue(fixture_usuario))
        registro_id = Rol.objects.first().id if ruta == ROLES else Deporte.objects.first().id

        assert _usos(api, ruta, registro_id).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize('ruta', [DEPORTES, SERVICIOS, ROLES])
    def test_solo_admite_lectura(self, api, rbac, ruta):
        registro_id = Rol.objects.first().id if ruta == ROLES else Deporte.objects.first().id

        assert api.post(f'{ruta}{registro_id}/usos/', {}, format='json').status_code == 405
        assert api.delete(f'{ruta}{registro_id}/usos/').status_code == 405

    @pytest.mark.parametrize('ruta', [DEPORTES, SERVICIOS, ROLES])
    def test_id_inexistente_responde_404(self, api, rbac, ruta):
        assert _usos(api, ruta, 999999).status_code == status.HTTP_404_NOT_FOUND

    def test_el_permiso_de_roles_no_abre_los_usos_de_catalogos_y_viceversa(self, rbac, crear_usuario, cliente_de):
        # Un rol personalizado con un solo permiso de sistema no se puede crear por API; se arma a mano para probar el cruce.
        from core.models import Permiso, RolPermiso

        rol = Rol.objects.create(nombre='Solo Catalogos')
        RolPermiso.objects.create(rol=rol, permiso=Permiso.objects.get(codigo='administrar_catalogos'))
        usuario = crear_usuario('catalogos@talibre.test', 'JUGADOR')
        Usuario.objects.filter(pk=usuario.pk).update(rol=rol)
        api = cliente_de(Usuario.objects.get(pk=usuario.pk))

        assert _usos(api, DEPORTES, _id(Deporte, nombre='Fútbol 5')).status_code == status.HTTP_200_OK
        assert _usos(api, SERVICIOS, _id(Servicio, nombre='Buffet')).status_code == status.HTTP_200_OK
        assert _usos(api, ROLES, rol.id).status_code == status.HTTP_403_FORBIDDEN


class TestUsosDeDeporte:
    def test_agrupa_las_canchas_por_complejo(self, api, complejo, complejo_ajeno, crear_cancha):
        crear_cancha(complejo, 'Cancha 2', 'Fútbol 5')
        crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
        crear_cancha(complejo_ajeno, 'Cancha A', 'Fútbol 5')
        crear_cancha(complejo, 'Pádel 1', 'Pádel')

        respuesta = _usos(api, DEPORTES, _id(Deporte, nombre='Fútbol 5'))

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert cuerpo['count'] == 2
        assert cuerpo['next'] is None
        ajeno, propio = cuerpo['results']
        assert set(propio) == {'complejo_id', 'complejo_nombre', 'canchas'}
        assert propio['complejo_id'] == complejo.id
        assert propio['complejo_nombre'] == 'Complejo Propio'
        assert [cancha['nombre'] for cancha in propio['canchas']] == ['Cancha 1', 'Cancha 2']
        assert set(propio['canchas'][0]) == {'id', 'nombre'}
        assert ajeno['complejo_id'] == complejo_ajeno.id
        assert [cancha['nombre'] for cancha in ajeno['canchas']] == ['Cancha A']

    def test_sin_usos_devuelve_una_lista_vacia(self, api, rbac):
        respuesta = _usos(api, DEPORTES, _id(Deporte, nombre='Tenis'))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json() == {'count': 0, 'next': None, 'previous': None, 'results': []}

    def test_excluye_las_canchas_dadas_de_baja_pero_no_las_en_mantenimiento(self, api, complejo, crear_cancha):
        crear_cancha(complejo, 'Vigente', 'Fútbol 5')
        crear_cancha(complejo, 'En arreglo', 'Fútbol 5', estado=EstadoCancha.EN_MANTENIMIENTO)
        crear_cancha(complejo, 'Eliminada', 'Fútbol 5', estado=EstadoCancha.BAJA)

        resultado = _usos(api, DEPORTES, _id(Deporte, nombre='Fútbol 5')).json()['results']

        assert [cancha['nombre'] for cancha in resultado[0]['canchas']] == ['En arreglo', 'Vigente']

    def test_un_complejo_con_todas_sus_canchas_de_baja_no_figura(self, api, complejo, crear_cancha):
        crear_cancha(complejo, 'Eliminada', 'Fútbol 5', estado=EstadoCancha.BAJA)

        assert _usos(api, DEPORTES, _id(Deporte, nombre='Fútbol 5')).json()['count'] == 0

    def test_coincide_con_la_cantidad_que_bloquea_la_baja(self, api, complejo, complejo_ajeno, crear_cancha):
        crear_cancha(complejo, 'C1', 'Fútbol 5')
        crear_cancha(complejo, 'C2', 'Fútbol 5', estado=EstadoCancha.EN_MANTENIMIENTO)
        crear_cancha(complejo, 'C3', 'Fútbol 5', estado=EstadoCancha.BAJA)
        crear_cancha(complejo_ajeno, 'C4', 'Fútbol 5')
        deporte_id = _id(Deporte, nombre='Fútbol 5')

        resultado = _usos(api, DEPORTES, deporte_id).json()['results']

        assert sum(len(item['canchas']) for item in resultado) == _cantidad_listada(api, DEPORTES, deporte_id) == 3
        assert api.delete(f'{DEPORTES}{deporte_id}/').status_code == status.HTTP_400_BAD_REQUEST

    def test_responde_para_un_deporte_dado_de_baja(self, api, rbac):
        Deporte.objects.get(nombre='Tenis').desactivar()

        assert _usos(api, DEPORTES, _id(Deporte, nombre='Tenis')).status_code == status.HTTP_200_OK

    def test_pagina_de_a_veinte_complejos(self, api, crear_usuario, crear_complejo, crear_cancha):
        dueno = crear_usuario('muchos@talibre.test', 'DUENO_COMPLEJO')
        for numero in range(25):
            crear_cancha(crear_complejo(dueno, f'Complejo {numero:02d}'), 'Cancha 1', 'Fútbol 5')
        deporte_id = _id(Deporte, nombre='Fútbol 5')

        primera = _usos(api, DEPORTES, deporte_id).json()
        segunda = api.get(f'{DEPORTES}{deporte_id}/usos/?page=2').json()

        assert primera['count'] == 25
        assert len(primera['results']) == 20
        assert primera['next'] is not None
        assert len(segunda['results']) == 5

    def test_no_hace_una_consulta_por_complejo(self, api, crear_usuario, crear_complejo, crear_cancha,
                                               django_assert_max_num_queries):
        dueno = crear_usuario('muchos@talibre.test', 'DUENO_COMPLEJO')
        for numero in range(12):
            complejo = crear_complejo(dueno, f'Complejo {numero:02d}')
            crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
            crear_cancha(complejo, 'Cancha 2', 'Fútbol 5')
        deporte_id = _id(Deporte, nombre='Fútbol 5')

        with django_assert_max_num_queries(10):
            assert _usos(api, DEPORTES, deporte_id).status_code == status.HTTP_200_OK


class TestUsosDeServicio:
    def test_lista_los_complejos_que_lo_ofrecen(self, api, complejo, complejo_ajeno, ofrecer_servicios):
        ofrecer_servicios(complejo_ajeno, 'Buffet')
        ofrecer_servicios(complejo, 'Buffet', 'Duchas')

        respuesta = _usos(api, SERVICIOS, _id(Servicio, nombre='Buffet'))

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert cuerpo['count'] == 2
        assert [item['complejo_nombre'] for item in cuerpo['results']] == ['Complejo Ajeno', 'Complejo Propio']
        assert set(cuerpo['results'][0]) == {'complejo_id', 'complejo_nombre'}
        assert cuerpo['results'][1]['complejo_id'] == complejo.id

    def test_sin_usos_devuelve_una_lista_vacia(self, api, rbac):
        respuesta = _usos(api, SERVICIOS, _id(Servicio, nombre='Wi-Fi'))

        assert respuesta.json() == {'count': 0, 'next': None, 'previous': None, 'results': []}

    def test_excluye_las_ofertas_dadas_de_baja_y_los_complejos_dados_de_baja(
        self, api, complejo, complejo_ajeno, crear_complejo, dueno, ofrecer_servicios,
    ):
        ofrecer_servicios(complejo, 'Buffet')[0]
        ofrecer_servicios(complejo_ajeno, 'Buffet')[0].desactivar()
        eliminado = crear_complejo(dueno, 'Complejo Eliminado')
        ofrecer_servicios(eliminado, 'Buffet')
        eliminado.desactivar()

        resultado = _usos(api, SERVICIOS, _id(Servicio, nombre='Buffet')).json()['results']

        assert [item['complejo_id'] for item in resultado] == [complejo.id]

    def test_coincide_con_la_cantidad_que_bloquea_la_baja(self, api, complejo, complejo_ajeno, ofrecer_servicios):
        ofrecer_servicios(complejo, 'Buffet')
        ofrecer_servicios(complejo_ajeno, 'Buffet')[0].desactivar()
        servicio_id = _id(Servicio, nombre='Buffet')

        cuerpo = _usos(api, SERVICIOS, servicio_id).json()

        assert cuerpo['count'] == _cantidad_listada(api, SERVICIOS, servicio_id) == 1
        assert api.delete(f'{SERVICIOS}{servicio_id}/').status_code == status.HTTP_400_BAD_REQUEST

    def test_una_oferta_reactivada_vuelve_a_figurar(self, api, complejo, ofrecer_servicios):
        oferta = ofrecer_servicios(complejo, 'Buffet')[0]
        oferta.desactivar()
        ComplejoServicio.objects.filter(pk=oferta.pk).update(estado=EstadoRegistro.ACTIVO)

        assert _usos(api, SERVICIOS, _id(Servicio, nombre='Buffet')).json()['count'] == 1

    def test_no_hace_una_consulta_por_complejo(self, api, crear_usuario, crear_complejo, ofrecer_servicios,
                                               django_assert_max_num_queries):
        dueno = crear_usuario('muchos@talibre.test', 'DUENO_COMPLEJO')
        for numero in range(12):
            ofrecer_servicios(crear_complejo(dueno, f'Complejo {numero:02d}'), 'Buffet')
        servicio_id = _id(Servicio, nombre='Buffet')

        with django_assert_max_num_queries(8):
            assert _usos(api, SERVICIOS, servicio_id).status_code == status.HTTP_200_OK


class TestUsosDeRol:
    def test_lista_las_cuentas_activas_y_suspendidas(self, api, jugador, crear_usuario):
        crear_usuario('suspendido@talibre.test', 'JUGADOR', estado=EstadoUsuario.SUSPENDIDO, nombre_completo='Ana Suspendida')

        respuesta = _usos(api, ROLES, _id(Rol, nombre='JUGADOR'))

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert cuerpo['count'] == 2
        assert [item['nombre'] for item in cuerpo['results']] == ['Ana Suspendida', 'Jugador Prueba']
        assert set(cuerpo['results'][0]) == {'id', 'nombre', 'email', 'estado', 'estado_nombre'}
        assert cuerpo['results'][0]['estado'] == EstadoUsuario.SUSPENDIDO
        assert cuerpo['results'][0]['email'] == 'suspendido@talibre.test'
        assert cuerpo['results'][1]['id'] == jugador.id

    def test_excluye_las_cuentas_dadas_de_baja(self, api, jugador, crear_usuario):
        crear_usuario('baja@talibre.test', 'JUGADOR', estado=EstadoUsuario.BAJA)

        resultado = _usos(api, ROLES, _id(Rol, nombre='JUGADOR')).json()

        assert [item['id'] for item in resultado['results']] == [jugador.id]

    def test_sin_usos_devuelve_una_lista_vacia(self, api, rbac):
        rol = Rol.objects.create(nombre='Sin Cuentas')

        assert _usos(api, ROLES, rol.id).json() == {'count': 0, 'next': None, 'previous': None, 'results': []}

    def test_coincide_con_la_cantidad_que_bloquea_la_baja(self, api, rbac, crear_usuario):
        rol = Rol.objects.create(nombre='Encargado')
        for correo, estado in (
            ('uno@talibre.test', EstadoUsuario.ACTIVO),
            ('dos@talibre.test', EstadoUsuario.SUSPENDIDO),
            ('tres@talibre.test', EstadoUsuario.BAJA),
        ):
            usuario = crear_usuario(correo, 'JUGADOR', estado=estado)
            Usuario.objects.filter(pk=usuario.pk).update(rol=rol)

        cuerpo = _usos(api, ROLES, rol.id).json()

        assert cuerpo['count'] == _cantidad_listada(api, ROLES, rol.id) == 2
        assert api.delete(f'{ROLES}{rol.id}/').status_code == status.HTTP_400_BAD_REQUEST

    def test_los_roles_base_tambien_se_consultan(self, api, superadmin):
        resultado = _usos(api, ROLES, _id(Rol, nombre='SUPERADMIN')).json()

        assert [item['id'] for item in resultado['results']] == [superadmin.id]

    def test_pagina_de_a_veinte_cuentas(self, api, crear_usuario):
        for numero in range(22):
            crear_usuario(f'jugador{numero}@talibre.test', 'JUGADOR', nombre_completo=f'Jugador {numero:02d}')
        rol_id = _id(Rol, nombre='JUGADOR')

        primera = _usos(api, ROLES, rol_id).json()
        segunda = api.get(f'{ROLES}{rol_id}/usos/?page=2').json()

        assert primera['count'] == 22
        assert len(primera['results']) == 20
        assert len(segunda['results']) == 2
