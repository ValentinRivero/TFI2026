import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import EstadoContrato, LogAuditoria, TipoEventoAuditoria


def _url(complejo_id):
    return f'/api/complejos/{complejo_id}/acceso/'


@pytest.mark.django_db
class TestAccesoAlComplejo:
    """Verificación que usa backend-node para saber si el usuario del token administra un complejo."""

    def test_el_dueno_administra_su_complejo(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).get(_url(complejo.id))

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json() == {'complejo': complejo.id}

    def test_el_operador_administra_el_complejo_asignado(self, operador, complejo, cliente_de):
        assert cliente_de(operador).get(_url(complejo.id)).status_code == status.HTTP_200_OK

    def test_el_superadmin_administra_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        assert cliente_de(superadmin).get(_url(complejo_ajeno.id)).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize('rol', ['dueno', 'operador'])
    def test_un_complejo_ajeno_responde_404_sin_confirmar_que_existe(self, request, rol, complejo_ajeno, cliente_de):
        usuario = request.getfixturevalue(rol)

        respuesta = cliente_de(usuario).get(_url(complejo_ajeno.id))

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        assert respuesta.json()['detail'] == cliente_de(usuario).get(_url(999999)).json()['detail']

    def test_el_jugador_recibe_403_auditado(self, jugador, complejo, cliente_de):
        assert cliente_de(jugador).get(_url(complejo.id)).status_code == status.HTTP_403_FORBIDDEN
        assert LogAuditoria.objects.filter(
            usuario=jugador, tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO,
        ).exists()

    def test_sin_token_responde_401(self, complejo):
        assert APIClient().get(_url(complejo.id)).status_code == status.HTTP_401_UNAUTHORIZED

    def test_con_token_invalido_responde_401(self, complejo):
        cliente = APIClient()
        cliente.credentials(HTTP_AUTHORIZATION='Bearer no-es-un-jwt')

        assert cliente.get(_url(complejo.id)).status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize('estado_contrato', [EstadoContrato.PENDIENTE, EstadoContrato.SUSPENDIDO])
    def test_el_dueno_conserva_el_acceso_con_el_contrato_no_activo(
        self, dueno, complejo, cliente_de, estado_contrato,
    ):
        complejo.estado_contrato = estado_contrato
        complejo.save(update_fields=['estado_contrato'])

        assert cliente_de(dueno).get(_url(complejo.id)).status_code == status.HTTP_200_OK

    def test_un_complejo_dado_de_baja_responde_404(self, superadmin, complejo, cliente_de):
        complejo.desactivar()

        assert cliente_de(superadmin).get(_url(complejo.id)).status_code == status.HTTP_404_NOT_FOUND

    def test_solo_admite_get(self, dueno, complejo, cliente_de):
        assert cliente_de(dueno).post(_url(complejo.id)).status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_resuelve_en_consultas_constantes(
        self, dueno, complejo, crear_complejo, cliente_de, django_assert_max_num_queries,
    ):
        for numero in range(5):
            crear_complejo(dueno, f'Otro {numero}')
        cliente = cliente_de(dueno)

        with django_assert_max_num_queries(6):
            cliente.get(_url(complejo.id))
