from unittest import mock

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from django.http import Http404
from django.test import override_settings
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, Throttled

from core.exceptions import ConflictoNegocio, custom_exception_handler
from core.models import LogAuditoria, TipoEventoAuditoria


def _manejar(exc):
    return custom_exception_handler(exc, {'request': None, 'view': None})


class TestHealth:
    def test_health_es_publico_y_devuelve_200(self, cliente, db):
        respuesta = cliente.get('/api/health/')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json() == {'estado': 'ok'}

    def test_health_ignora_un_token_invalido(self, cliente, db):
        cliente.credentials(HTTP_AUTHORIZATION='Bearer token-roto')

        assert cliente.get('/api/health/').status_code == status.HTTP_200_OK


class TestFormatoDeErrores:
    def test_401_sin_token(self, cliente, db):
        respuesta = cliente.get('/api/perfil/')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json() == {'error': True, 'detail': 'Debés iniciar sesión para acceder a este recurso.'}

    def test_401_con_token_invalido(self, cliente, db):
        cliente.credentials(HTTP_AUTHORIZATION='Bearer token-roto')

        respuesta = cliente.get('/api/perfil/')

        assert respuesta.status_code == status.HTTP_401_UNAUTHORIZED
        assert respuesta.json() == {'error': True, 'detail': 'El token es inválido o expiró.'}

    def test_400_conserva_el_detalle_por_campo(self, cliente, db):
        respuesta = cliente.post('/api/registro/', {}, format='json')

        cuerpo = respuesta.json()
        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert cuerpo['error'] is True
        assert {'nombre_completo', 'email', 'password'}.issubset(cuerpo['detail'])

    def test_405_ante_metodo_no_permitido(self, jugador, cliente_de):
        respuesta = cliente_de(jugador).put('/api/perfil/', {}, format='json')

        assert respuesta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert respuesta.json() == {
            'error': True,
            'detail': 'El método de la solicitud no está permitido en este recurso.',
        }

    def test_409_de_negocio(self):
        respuesta = _manejar(ConflictoNegocio('El turno se superpone con una reserva existente.'))

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.data == {'error': True, 'detail': 'El turno se superpone con una reserva existente.'}

    def test_409_con_mensaje_por_defecto(self):
        respuesta = _manejar(ConflictoNegocio())

        assert respuesta.status_code == status.HTTP_409_CONFLICT
        assert respuesta.data['detail'] == ConflictoNegocio.default_detail

    def test_404_de_django_en_espanol(self):
        respuesta = _manejar(Http404())

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        assert respuesta.data == {'error': True, 'detail': 'No se encontró el recurso solicitado.'}

    def test_validation_error_de_django_se_convierte_en_400(self):
        respuesta = _manejar(DjangoValidationError({'hora_fin': ['Debe ser posterior a hora_inicio.']}))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert respuesta.data == {'error': True, 'detail': {'hora_fin': ['Debe ser posterior a hora_inicio.']}}

    def test_permission_denied_generico_en_espanol(self):
        respuesta = _manejar(PermissionDenied())

        assert respuesta.data == {'error': True, 'detail': 'No tenés permiso para realizar esta acción.'}

    def test_throttled_informa_la_espera(self):
        respuesta = _manejar(Throttled(wait=42))

        assert respuesta.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert respuesta.data['detail'] == 'Superaste el límite de solicitudes. Intentá nuevamente en 42 segundos.'
        assert respuesta['Retry-After'] == '42'

    @override_settings(DEBUG=False)
    def test_error_no_controlado_devuelve_500_generico(self):
        respuesta = _manejar(RuntimeError('detalle interno que no debe salir'))

        assert respuesta.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert respuesta.data == {'error': True, 'detail': 'Error interno del servidor.'}

    @pytest.mark.django_db
    @override_settings(DEBUG=False)
    def test_error_no_controlado_revierte_la_transaccion_de_la_peticion(self):
        with mock.patch.dict(connection.settings_dict, {'ATOMIC_REQUESTS': True}):
            with transaction.atomic():
                _manejar(RuntimeError('falla a mitad de la escritura'))
                assert transaction.get_rollback() is True

    @override_settings(DEBUG=True)
    def test_error_no_controlado_en_debug_se_propaga(self):
        assert _manejar(RuntimeError('falla')) is None

    @pytest.mark.django_db
    def test_sin_request_no_audita(self):
        _manejar(PermissionDenied())

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO).exists()
