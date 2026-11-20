from datetime import time, timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from core.models import (
    Deporte,
    DiaSemana,
    EstadoCancha,
    EstadoContrato,
    EstadoRegistro,
    HorarioApertura,
    LogAuditoria,
    Servicio,
    TipoEventoAuditoria,
)

CAMPOS_EXPUESTOS = {
    'id', 'nombre', 'estado', 'estado_nombre', 'usos', 'fecha_creacion', 'fecha_modificacion',
}

# Cada catálogo con su ruta administrativa, su ruta pública, su modelo y un ítem libre y otro usado por la fixture.
CATALOGOS = {
    'deportes': {
        'modelo': Deporte, 'admin': '/api/sistema/deportes/', 'publica': '/api/deportes/',
        'libre': 'Hockey', 'usado': 'Fútbol 5', 'etiqueta': 'deporte', 'largo': 60,
    },
    'servicios': {
        'modelo': Servicio, 'admin': '/api/sistema/servicios/', 'publica': '/api/servicios/',
        'libre': 'Lavandería', 'usado': 'Estacionamiento', 'etiqueta': 'servicio', 'largo': 80,
    },
}


@pytest.fixture(params=list(CATALOGOS))
def catalogo(request):
    return CATALOGOS[request.param]


@pytest.fixture
def api(superadmin, cliente_de):
    return cliente_de(superadmin)


@pytest.fixture
def en_uso(complejo, crear_cancha, ofrecer_servicios):
    crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
    ofrecer_servicios(complejo, 'Estacionamiento')


def _nombres(respuesta):
    return [registro['nombre'] for registro in respuesta.json()]


def _auditoria():
    return LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_CATALOGO)


def _item(catalogo, nombre):
    return catalogo['modelo'].objects.get(nombre=nombre)


class TestPermisos:
    def test_anonimo_recibe_401(self, cliente, rbac, catalogo):
        assert cliente.get(catalogo['admin']).status_code == status.HTTP_401_UNAUTHORIZED
        assert cliente.post(catalogo['admin'], {'nombre': 'Nuevo'}, format='json').status_code == 401

    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno'])
    def test_roles_sin_permiso_reciben_403_en_todas_las_operaciones(self, request, cliente_de, catalogo,
                                                                    fixture_usuario):
        api = cliente_de(request.getfixturevalue(fixture_usuario))
        registro = _item(catalogo, catalogo['usado'])
        detalle = f'{catalogo["admin"]}{registro.id}/'

        assert api.get(catalogo['admin']).status_code == status.HTTP_403_FORBIDDEN
        assert api.get(detalle).status_code == status.HTTP_403_FORBIDDEN
        assert api.post(catalogo['admin'], {'nombre': 'Nuevo'}, format='json').status_code == 403
        assert api.patch(detalle, {'nombre': 'Otro'}, format='json').status_code == status.HTTP_403_FORBIDDEN
        assert api.delete(detalle).status_code == status.HTTP_403_FORBIDDEN
        registro.refresh_from_db()
        assert registro.nombre == catalogo['usado']
        assert registro.estado == EstadoRegistro.ACTIVO

    def test_el_rechazo_por_rol_queda_en_auditoria(self, jugador, cliente_de, catalogo):
        cliente_de(jugador).post(catalogo['admin'], {'nombre': 'Nuevo'}, format='json')

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO).exists()
        assert not _auditoria().exists()

    def test_la_ruta_administrativa_no_acepta_put(self, api, catalogo):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = api.put(f'{catalogo["admin"]}{registro.id}/', {'nombre': 'Otro'}, format='json')

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestListado:
    def test_lista_todo_incluyendo_bajas_sin_paginar(self, api, catalogo):
        baja = catalogo['modelo'].objects.create(nombre=catalogo['libre'])
        baja.desactivar()

        respuesta = api.get(catalogo['admin'])

        assert respuesta.status_code == status.HTTP_200_OK
        assert isinstance(respuesta.json(), list)
        assert set(respuesta.json()[0]) == CAMPOS_EXPUESTOS
        por_nombre = {registro['nombre']: registro for registro in respuesta.json()}
        assert por_nombre[catalogo['libre']]['estado'] == EstadoRegistro.BAJA
        assert por_nombre[catalogo['libre']]['estado_nombre'] == 'Baja lógica'
        assert _nombres(respuesta) == sorted(_nombres(respuesta))

    def test_informa_cuantos_usos_vigentes_tiene_cada_item(self, api, catalogo, en_uso):
        por_nombre = {registro['nombre']: registro for registro in api.get(catalogo['admin']).json()}

        assert por_nombre[catalogo['usado']]['usos'] == 1
        assert all(
            registro['usos'] == 0 for nombre, registro in por_nombre.items() if nombre != catalogo['usado']
        )

    def test_los_usos_ignoran_canchas_dadas_de_baja(self, api, complejo, crear_cancha):
        cancha = crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
        cancha.estado = EstadoCancha.BAJA
        cancha.save(update_fields=['estado'])

        por_nombre = {r['nombre']: r for r in api.get(CATALOGOS['deportes']['admin']).json()}

        assert por_nombre['Fútbol 5']['usos'] == 0

    def test_los_usos_de_un_servicio_ignoran_asignaciones_dadas_de_baja(self, api, complejo, ofrecer_servicios):
        ofrecer_servicios(complejo, 'Wi-Fi')[0].desactivar()

        por_nombre = {r['nombre']: r for r in api.get(CATALOGOS['servicios']['admin']).json()}

        assert por_nombre['Wi-Fi']['usos'] == 0

    def test_detalle(self, api, catalogo):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = api.get(f'{catalogo["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['nombre'] == catalogo['usado']

    def test_detalle_inexistente_responde_404(self, api, catalogo):
        assert api.get(f'{catalogo["admin"]}999999/').status_code == status.HTTP_404_NOT_FOUND


class TestAlta:
    def test_crea_y_audita(self, api, superadmin, catalogo):
        respuesta = api.post(catalogo['admin'], {'nombre': catalogo['libre']}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert set(respuesta.json()) == CAMPOS_EXPUESTOS
        assert respuesta.json()['usos'] == 0
        assert respuesta.json()['estado'] == EstadoRegistro.ACTIVO
        registro = _item(catalogo, catalogo['libre'])
        log = _auditoria().get()
        assert log.usuario_id == superadmin.id
        assert log.accion == f'Alta de {catalogo["etiqueta"]}'
        assert f'id {registro.id}' in log.detalle

    def test_el_nuevo_item_aparece_en_la_lectura_publica(self, api, cliente, catalogo):
        api.post(catalogo['admin'], {'nombre': catalogo['libre']}, format='json')

        assert catalogo['libre'] in _nombres(cliente.get(catalogo['publica']))

    def test_limpia_espacios_externos_e_internos(self, api, catalogo):
        respuesta = api.post(catalogo['admin'], {'nombre': '   Squash   de   pared  '}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['nombre'] == 'Squash de pared'

    def test_sanitiza_etiquetas_html(self, api, catalogo):
        respuesta = api.post(catalogo['admin'], {'nombre': 'Rugby<script>alert(1)</script>'}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert '<' not in respuesta.json()['nombre']

    @pytest.mark.parametrize('cuerpo', [{}, {'nombre': ''}, {'nombre': '   '}, {'nombre': None}, {'nombre': 'A'}])
    def test_rechaza_nombre_vacio_ausente_o_demasiado_corto(self, api, catalogo, cuerpo):
        respuesta = api.post(catalogo['admin'], cuerpo, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.json()['error'] is True
        assert not _auditoria().exists()

    def test_rechaza_nombre_demasiado_largo(self, api, catalogo):
        respuesta = api.post(catalogo['admin'], {'nombre': 'x' * (catalogo['largo'] + 1)}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_acepta_el_largo_maximo(self, api, catalogo):
        respuesta = api.post(catalogo['admin'], {'nombre': 'x' * catalogo['largo']}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize('variante', [
        lambda nombre: nombre,
        lambda nombre: nombre.upper(),
        lambda nombre: nombre.lower(),
        lambda nombre: f'  {nombre}  ',
        lambda nombre: nombre.replace(' ', '   '),
    ])
    def test_rechaza_duplicados_sin_distinguir_mayusculas_ni_espacios(self, api, catalogo, variante):
        # La comparación de mayúsculas de SQLite es solo ASCII: el ítem de prueba no lleva tildes.
        existente = catalogo['modelo'].objects.create(nombre='Ping Pong' if catalogo['etiqueta'] == 'deporte'
                                                      else 'Sala Cuna')
        cantidad = catalogo['modelo'].objects.count()

        respuesta = api.post(catalogo['admin'], {'nombre': variante(existente.nombre)}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Ya existe' in str(respuesta.json()['detail']['nombre'])
        assert catalogo['modelo'].objects.count() == cantidad
        assert not _auditoria().exists()

    def test_un_nombre_dado_de_baja_sigue_ocupado_y_sugiere_reactivar(self, api, catalogo):
        baja = catalogo['modelo'].objects.create(nombre='Ping Pong')
        baja.desactivar()

        respuesta = api.post(catalogo['admin'], {'nombre': 'ping pong'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Reactivalo' in str(respuesta.json()['detail']['nombre'])

    def test_una_carrera_con_la_restriccion_unica_responde_400(self, api, catalogo, monkeypatch):
        from core.repositories import CatalogoMaestroRepository

        catalogo['modelo'].objects.create(nombre='Ping Pong')
        monkeypatch.setattr(CatalogoMaestroRepository, 'con_nombre', classmethod(lambda cls, *a, **k: None))

        respuesta = api.post(catalogo['admin'], {'nombre': 'Ping Pong'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Ya existe' in str(respuesta.json()['detail']['nombre'])


class TestEdicion:
    def test_renombra_y_audita_el_nombre_anterior(self, api, superadmin, catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', {'nombre': '  Tenis de mesa '}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['nombre'] == 'Tenis de mesa'
        registro.refresh_from_db()
        assert registro.nombre == 'Tenis de mesa'
        log = _auditoria().get()
        assert log.accion == f'Modificación de {catalogo["etiqueta"]}'
        assert log.usuario_id == superadmin.id
        assert 'Antes: «Ping Pong»' in log.detalle

    def test_un_item_en_uso_se_puede_renombrar(self, api, catalogo, en_uso):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', {'nombre': 'Nombre Nuevo'}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['usos'] == 1

    def test_guardar_el_mismo_nombre_no_cambia_ni_audita(self, api, catalogo):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', {'nombre': catalogo['usado']}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert not _auditoria().exists()

    def test_cambiar_solo_las_mayusculas_del_propio_nombre_es_valido(self, api, catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', {'nombre': 'PING PONG'}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['nombre'] == 'PING PONG'

    def test_rechaza_el_nombre_de_otro_item_en_cualquier_capitalizacion(self, api, catalogo):
        catalogo['modelo'].objects.create(nombre='Ping Pong')
        registro = catalogo['modelo'].objects.create(nombre='Squash')

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', {'nombre': 'pING pONG'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        registro.refresh_from_db()
        assert registro.nombre == 'Squash'
        assert not _auditoria().exists()

    @pytest.mark.parametrize('cuerpo', [{}, {'nombre': ''}, {'nombre': '  '}, {'estado': 0}, {'estado': 7}])
    def test_rechaza_cuerpos_invalidos(self, api, catalogo, cuerpo):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', cuerpo, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        registro.refresh_from_db()
        assert registro.estado == EstadoRegistro.ACTIVO

    def test_inexistente_responde_404(self, api, catalogo):
        respuesta = api.patch(f'{catalogo["admin"]}999999/', {'nombre': 'Otro'}, format='json')

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    def test_reactiva_un_item_dado_de_baja(self, api, cliente, catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')
        registro.desactivar()
        assert 'Ping Pong' not in _nombres(cliente.get(catalogo['publica']))

        respuesta = api.patch(f'{catalogo["admin"]}{registro.id}/', {'estado': 1}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoRegistro.ACTIVO
        assert 'Ping Pong' in _nombres(cliente.get(catalogo['publica']))
        assert 'Reactivado' in _auditoria().get().detalle


class TestBaja:
    def test_da_de_baja_logica_y_audita(self, api, superadmin, cliente, catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')

        respuesta = api.delete(f'{catalogo["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        registro.refresh_from_db()
        assert registro.estado == EstadoRegistro.BAJA
        assert catalogo['modelo'].objects.filter(id=registro.id).exists()
        log = _auditoria().get()
        assert log.accion == f'Baja de {catalogo["etiqueta"]}'
        assert log.usuario_id == superadmin.id

    def test_la_baja_sale_de_la_lectura_publica_pero_sigue_en_el_listado_administrativo(self, api, cliente,
                                                                                         catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')
        api.delete(f'{catalogo["admin"]}{registro.id}/')

        assert 'Ping Pong' not in _nombres(cliente.get(catalogo['publica']))
        assert 'Ping Pong' in _nombres(api.get(catalogo['admin']))

    def test_bloquea_la_baja_de_un_item_en_uso(self, api, catalogo, en_uso):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = api.delete(f'{catalogo["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'está en uso' in respuesta.json()['detail']
        assert catalogo['usado'] in respuesta.json()['detail']
        registro.refresh_from_db()
        assert registro.estado == EstadoRegistro.ACTIVO
        assert not _auditoria().exists()

    def test_el_mensaje_cuenta_los_usos(self, api, complejo, crear_cancha):
        crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
        crear_cancha(complejo, 'Cancha 2', 'Fútbol 5')
        registro = Deporte.objects.get(nombre='Fútbol 5')

        respuesta = api.delete(f'{CATALOGOS["deportes"]["admin"]}{registro.id}/')

        assert '2 canchas' in respuesta.json()['detail']

    def test_un_deporte_cuyas_canchas_estan_de_baja_se_puede_dar_de_baja(self, api, complejo, crear_cancha):
        cancha = crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
        cancha.estado = EstadoCancha.BAJA
        cancha.save(update_fields=['estado'])
        registro = Deporte.objects.get(nombre='Fútbol 5')

        respuesta = api.delete(f'{CATALOGOS["deportes"]["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT

    def test_un_deporte_con_cancha_en_mantenimiento_cuenta_como_en_uso(self, api, complejo, crear_cancha):
        crear_cancha(complejo, 'Cancha 1', 'Fútbol 5', estado=EstadoCancha.EN_MANTENIMIENTO)
        registro = Deporte.objects.get(nombre='Fútbol 5')

        respuesta = api.delete(f'{CATALOGOS["deportes"]["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST

    def test_un_servicio_asignado_solo_a_complejos_de_baja_se_puede_dar_de_baja(self, api, complejo,
                                                                                ofrecer_servicios):
        ofrecer_servicios(complejo, 'Wi-Fi')
        complejo.estado = EstadoRegistro.BAJA
        complejo.save(update_fields=['estado'])
        registro = Servicio.objects.get(nombre='Wi-Fi')

        respuesta = api.delete(f'{CATALOGOS["servicios"]["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT

    def test_un_servicio_cuya_asignacion_se_quito_se_puede_dar_de_baja(self, api, complejo, ofrecer_servicios):
        ofrecer_servicios(complejo, 'Wi-Fi')[0].desactivar()
        registro = Servicio.objects.get(nombre='Wi-Fi')

        assert api.delete(f'{CATALOGOS["servicios"]["admin"]}{registro.id}/').status_code == 204

    def test_un_servicio_asignado_cuenta_como_en_uso_aunque_el_contrato_este_suspendido(
        self, api, complejo, ofrecer_servicios,
    ):
        ofrecer_servicios(complejo, 'Wi-Fi')
        complejo.estado_contrato = EstadoContrato.SUSPENDIDO
        complejo.save(update_fields=['estado_contrato'])
        registro = Servicio.objects.get(nombre='Wi-Fi')

        respuesta = api.delete(f'{CATALOGOS["servicios"]["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert '1 complejo' in respuesta.json()['detail']

    def test_dar_de_baja_dos_veces_responde_400(self, api, catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')
        api.delete(f'{catalogo["admin"]}{registro.id}/')

        respuesta = api.delete(f'{catalogo["admin"]}{registro.id}/')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert len(_auditoria()) == 1

    def test_inexistente_responde_404(self, api, catalogo):
        assert api.delete(f'{catalogo["admin"]}999999/').status_code == status.HTTP_404_NOT_FOUND

    def test_nunca_hay_borrado_fisico(self, api, catalogo):
        registro = catalogo['modelo'].objects.create(nombre='Ping Pong')
        total = catalogo['modelo'].objects.count()

        api.delete(f'{catalogo["admin"]}{registro.id}/')

        assert catalogo['modelo'].objects.count() == total


class TestLecturaPublicaIntacta:
    def test_la_ruta_publica_sigue_igual_para_anonimos(self, cliente, rbac, catalogo):
        respuesta = cliente.get(catalogo['publica'])

        assert respuesta.status_code == status.HTTP_200_OK
        assert set(respuesta.json()[0]) == {'id', 'nombre'}

    @pytest.mark.parametrize('metodo', ['post', 'patch', 'delete', 'put'])
    def test_la_ruta_publica_no_admite_mutaciones(self, api, catalogo, metodo):
        registro = _item(catalogo, catalogo['usado'])

        respuesta = getattr(api, metodo)(f'{catalogo["publica"]}{registro.id}/', {'nombre': 'X'}, format='json')

        assert respuesta.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED)
        assert api.post(catalogo['publica'], {'nombre': 'X'}, format='json').status_code == 405


class TestInvalidacionDeLaGrilla:
    @pytest.fixture
    def lunes(self):
        manana = timezone.localdate() + timedelta(days=1)
        return manana + timedelta(days=(DiaSemana.LUNES - manana.weekday()) % 7)

    def _nombre_del_deporte_en_la_grilla(self, cliente, complejo, fecha):
        respuesta = cliente.get(f'/api/complejos/{complejo.id}/grilla/?fecha={fecha.isoformat()}')
        assert respuesta.status_code == status.HTTP_200_OK
        return respuesta.json()['canchas'][0]['deporte']['nombre']

    def test_renombrar_un_deporte_refresca_la_grilla_cacheada(
        self, api, cliente, complejo, crear_cancha, lunes, django_capture_on_commit_callbacks,
    ):
        cancha = crear_cancha(complejo, 'Cancha 1', 'Fútbol 5')
        HorarioApertura.objects.create(
            cancha=cancha, dia_semana=DiaSemana.LUNES, hora_apertura=time(14), hora_cierre=time(16),
        )
        assert self._nombre_del_deporte_en_la_grilla(cliente, complejo, lunes) == 'Fútbol 5'

        with django_capture_on_commit_callbacks(execute=True):
            respuesta = api.patch(
                f'{CATALOGOS["deportes"]["admin"]}{cancha.deporte_id}/', {'nombre': 'Fútbol Cinco'}, format='json',
            )

        assert respuesta.status_code == status.HTTP_200_OK
        assert self._nombre_del_deporte_en_la_grilla(cliente, complejo, lunes) == 'Fútbol Cinco'
