"""
Verifica la doble capa de acceso con un ViewSet mínimo de canchas que existe solo en estas pruebas:
visibilidad por get_queryset (404 ante lo ajeno) y operación por permisos, perform_create y perform_update (403).
"""
from decimal import Decimal

import pytest
from rest_framework import serializers, status, viewsets
from rest_framework.routers import SimpleRouter

from core.models import (
    Cancha,
    Cobertura,
    Deporte,
    EstadoRegistro,
    Iluminacion,
    LogAuditoria,
    TipoEventoAuditoria,
    TipoSuperficie,
)
from core.permissions import AdministraComplejo, TienePermisoRBAC
from core.views import AccesoComplejoMixin


class CanchaPruebaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cancha
        fields = ('id', 'complejo', 'deporte', 'nombre', 'tipo_superficie', 'cobertura', 'iluminacion', 'precio_base')


class CanchaPruebaViewSet(AccesoComplejoMixin, viewsets.ModelViewSet):
    queryset = Cancha.objects.exclude(estado=EstadoRegistro.BAJA).order_by('id')
    serializer_class = CanchaPruebaSerializer
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'list': ('ver_canchas',),
        'retrieve': ('ver_canchas',),
        'create': ('administrar_canchas',),
        'partial_update': ('administrar_canchas',),
    }
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filter_backends = []


router = SimpleRouter()
router.register('canchas-prueba', CanchaPruebaViewSet, basename='cancha-prueba')
urlpatterns = router.urls

pytestmark = pytest.mark.urls('core.tests.test_acceso_complejos')

URL = '/canchas-prueba/'


def _crear_cancha(complejo, nombre):
    return Cancha.objects.create(
        complejo=complejo,
        deporte=Deporte.objects.get(nombre='Fútbol 5'),
        nombre=nombre,
        tipo_superficie=TipoSuperficie.CESPED_SINTETICO,
        cobertura=Cobertura.DESCUBIERTA,
        iluminacion=Iluminacion.LED,
        precio_base=Decimal('38000.00'),
    )


def _datos_alta(complejo, nombre='Cancha Nueva'):
    return {
        'complejo': complejo.id,
        'deporte': Deporte.objects.get(nombre='Fútbol 5').id,
        'nombre': nombre,
        'tipo_superficie': TipoSuperficie.CESPED_SINTETICO,
        'cobertura': Cobertura.TECHADA,
        'iluminacion': Iluminacion.LED,
        'precio_base': '40000.00',
    }


@pytest.fixture
def cancha_propia(complejo):
    return _crear_cancha(complejo, 'Cancha Propia')


@pytest.fixture
def cancha_ajena(complejo_ajeno):
    return _crear_cancha(complejo_ajeno, 'Cancha Ajena')


class TestVisibilidad:
    def test_dueno_lista_solo_las_canchas_de_su_complejo(self, dueno, cancha_propia, cancha_ajena, cliente_de):
        respuesta = cliente_de(dueno).get(URL)

        assert respuesta.status_code == status.HTTP_200_OK
        assert [cancha['id'] for cancha in respuesta.json()['results']] == [cancha_propia.id]

    def test_dueno_recibe_404_ante_una_cancha_ajena(self, dueno, cancha_ajena, cliente_de):
        respuesta = cliente_de(dueno).get(f'{URL}{cancha_ajena.id}/')

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        assert respuesta.json() == {'error': True, 'detail': 'No se encontró el recurso solicitado.'}

    def test_el_404_ajeno_es_igual_al_de_un_recurso_inexistente(self, dueno, cancha_ajena, cliente_de):
        cliente = cliente_de(dueno)

        ajena = cliente.get(f'{URL}{cancha_ajena.id}/')
        inexistente = cliente.get(f'{URL}999999/')

        assert ajena.status_code == inexistente.status_code == status.HTTP_404_NOT_FOUND
        assert ajena.json() == inexistente.json()

    def test_el_404_ajeno_no_se_audita_como_acceso_denegado(self, dueno, cancha_ajena, cliente_de):
        cliente_de(dueno).get(f'{URL}{cancha_ajena.id}/')

        assert not LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO).exists()

    def test_dueno_ve_su_cancha(self, dueno, cancha_propia, cliente_de):
        assert cliente_de(dueno).get(f'{URL}{cancha_propia.id}/').status_code == status.HTTP_200_OK

    def test_operador_ve_solo_su_complejo_operado(self, operador, cancha_propia, cancha_ajena, cliente_de):
        cliente = cliente_de(operador)

        assert [c['id'] for c in cliente.get(URL).json()['results']] == [cancha_propia.id]
        assert cliente.get(f'{URL}{cancha_ajena.id}/').status_code == status.HTTP_404_NOT_FOUND

    def test_superadmin_ve_todas_las_canchas(self, superadmin, cancha_propia, cancha_ajena, cliente_de):
        cliente = cliente_de(superadmin)

        assert {c['id'] for c in cliente.get(URL).json()['results']} == {cancha_propia.id, cancha_ajena.id}
        assert cliente.get(f'{URL}{cancha_ajena.id}/').status_code == status.HTTP_200_OK

    def test_complejo_dado_de_baja_oculta_sus_canchas(self, dueno, complejo, cancha_propia, cliente_de):
        complejo.desactivar()

        assert cliente_de(dueno).get(f'{URL}{cancha_propia.id}/').status_code == status.HTTP_404_NOT_FOUND


class TestPermisosDeOperacion:
    def test_jugador_recibe_403_al_listar(self, jugador, cliente_de):
        assert cliente_de(jugador).get(URL).status_code == status.HTTP_403_FORBIDDEN

    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_operador_no_puede_dar_de_alta_canchas(self, operador, complejo, cliente_de):
        respuesta = cliente_de(operador).post(URL, _datos_alta(complejo), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert not Cancha.objects.filter(nombre='Cancha Nueva').exists()


class TestControlEnPerformCreate:
    def test_dueno_crea_en_su_complejo(self, dueno, complejo, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert Cancha.objects.get(nombre='Cancha Nueva').complejo == complejo

    def test_dueno_no_crea_en_complejo_ajeno(self, dueno, complejo_ajeno, cliente_de):
        respuesta = cliente_de(dueno).post(URL, _datos_alta(complejo_ajeno), format='json')

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        assert respuesta.json() == {'error': True, 'detail': 'No podés operar sobre recursos de este complejo.'}
        assert not Cancha.objects.filter(nombre='Cancha Nueva').exists()

    def test_el_alta_rechazada_queda_auditada(self, dueno, complejo_ajeno, cliente_de):
        cliente_de(dueno).post(URL, _datos_alta(complejo_ajeno), format='json')

        log = LogAuditoria.objects.get(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO)
        assert log.usuario == dueno
        assert log.accion == f'POST {URL}'

    def test_superadmin_crea_en_cualquier_complejo(self, superadmin, complejo_ajeno, cliente_de):
        respuesta = cliente_de(superadmin).post(URL, _datos_alta(complejo_ajeno), format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED


class TestControlEnPerformUpdate:
    def test_dueno_edita_su_cancha(self, dueno, cancha_propia, cliente_de):
        respuesta = cliente_de(dueno).patch(f'{URL}{cancha_propia.id}/', {'nombre': 'Renombrada'}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        cancha_propia.refresh_from_db()
        assert cancha_propia.nombre == 'Renombrada'

    def test_dueno_no_puede_mover_su_cancha_a_un_complejo_ajeno(
        self, dueno, cancha_propia, complejo, complejo_ajeno, cliente_de,
    ):
        respuesta = cliente_de(dueno).patch(
            f'{URL}{cancha_propia.id}/', {'complejo': complejo_ajeno.id}, format='json',
        )

        assert respuesta.status_code == status.HTTP_403_FORBIDDEN
        cancha_propia.refresh_from_db()
        assert cancha_propia.complejo == complejo

    def test_dueno_no_edita_canchas_ajenas(self, dueno, cancha_ajena, cliente_de):
        respuesta = cliente_de(dueno).patch(f'{URL}{cancha_ajena.id}/', {'nombre': 'Robada'}, format='json')

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        cancha_ajena.refresh_from_db()
        assert cancha_ajena.nombre == 'Cancha Ajena'
