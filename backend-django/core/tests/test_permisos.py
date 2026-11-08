import pytest

from core.models import Cancha, Complejo, EstadoUsuario, Permiso, Rol, RolPermiso
from core.permissions import AdministraComplejo, TienePermisoRBAC
from core.services import AccesoComplejoService, RbacService

PERFIL = {'ver_perfil_propio', 'editar_perfil_propio', 'desactivar_perfil_propio'}
RESERVAS_PROPIAS = {'reservar_turno', 'ver_reservas_propias', 'cancelar_reserva_propia'}
OPERATORIA = {
    'ver_panel_complejo', 'ver_canchas', 'ver_agenda', 'gestionar_agenda', 'cancelar_reserva_complejo',
    'gestionar_turnos_fijos', 'ver_excepciones', 'gestionar_excepciones',
}
GESTION_DEL_DUENO = {
    'configurar_complejo', 'administrar_canchas', 'administrar_horarios', 'administrar_precios',
    'ver_operadores', 'gestionar_operadores', 'ver_reportes',
}
SISTEMA = {
    'ver_panel_sistema', 'ver_contratos', 'administrar_contratos', 'ver_usuarios', 'editar_usuarios',
    'desactivar_usuarios', 'auditar_seguridad',
}
TODOS = PERFIL | RESERVAS_PROPIAS | OPERATORIA | GESTION_DEL_DUENO | SISTEMA

MATRIZ = {
    'jugador': PERFIL | RESERVAS_PROPIAS,
    'operador': PERFIL | OPERATORIA,
    'dueno': PERFIL | OPERATORIA | GESTION_DEL_DUENO,
    'superadmin': TODOS,
}


class TestMatrizRBAC:
    def test_el_catalogo_tiene_los_28_permisos(self, rbac):
        assert set(Permiso.objects.values_list('codigo', flat=True)) == TODOS
        assert len(TODOS) == 28

    @pytest.mark.parametrize('fixture_usuario', list(MATRIZ))
    def test_cada_rol_tiene_exactamente_sus_permisos(self, request, fixture_usuario):
        usuario = request.getfixturevalue(fixture_usuario)

        assert RbacService.permisos_de(usuario) == MATRIZ[fixture_usuario]

    @pytest.mark.parametrize('fixture_usuario', list(MATRIZ))
    @pytest.mark.parametrize('codigo', sorted(TODOS))
    def test_tiene_permiso_por_codigo(self, request, fixture_usuario, codigo):
        usuario = request.getfixturevalue(fixture_usuario)

        assert RbacService.tiene_permiso(usuario, codigo) is (codigo in MATRIZ[fixture_usuario])

    def test_usuario_anonimo_no_tiene_permisos(self, rbac):
        from django.contrib.auth.models import AnonymousUser

        assert RbacService.permisos_de(AnonymousUser()) == frozenset()


class TestSoloAsignacionesActivas:
    def test_asignacion_dada_de_baja_no_cuenta(self, jugador):
        RolPermiso.objects.get(rol__nombre='JUGADOR', permiso__codigo='reservar_turno').desactivar()

        assert not RbacService.tiene_permiso(jugador, 'reservar_turno')
        assert RbacService.tiene_permiso(type(jugador).objects.get(pk=jugador.pk), 'ver_reservas_propias')

    def test_permiso_dado_de_baja_no_cuenta_para_nadie(self, jugador, superadmin):
        Permiso.objects.get(codigo='reservar_turno').desactivar()

        assert not RbacService.tiene_permiso(jugador, 'reservar_turno')
        assert not RbacService.tiene_permiso(superadmin, 'reservar_turno')

    def test_rol_dado_de_baja_anula_sus_permisos(self, jugador):
        Rol.objects.get(nombre='JUGADOR').desactivar()

        assert RbacService.permisos_de(type(jugador).objects.get(pk=jugador.pk)) == frozenset()

    @pytest.mark.parametrize('estado', [EstadoUsuario.SUSPENDIDO, EstadoUsuario.BAJA])
    def test_usuario_no_activo_no_tiene_permisos(self, jugador, estado):
        jugador.estado = estado
        jugador.save(update_fields=['estado'])

        assert RbacService.permisos_de(jugador) == frozenset()

    def test_los_permisos_se_cachean_durante_la_peticion(self, jugador, django_assert_num_queries):
        RbacService.permisos_de(jugador)

        with django_assert_num_queries(0):
            assert RbacService.tiene_permisos(jugador, PERFIL)


class TestHerenciaSuperadmin:
    def _quitar_asignacion_directa(self, codigo):
        RolPermiso.objects.get(rol__nombre='SUPERADMIN', permiso__codigo=codigo).desactivar()

    def test_hereda_permisos_de_complejo_aunque_no_los_tenga_asignados(self, superadmin):
        self._quitar_asignacion_directa('gestionar_agenda')
        self._quitar_asignacion_directa('ver_reportes')

        assert RbacService.tiene_permiso(superadmin, 'gestionar_agenda')
        assert RbacService.tiene_permiso(superadmin, 'ver_reportes')

    def test_no_hereda_permisos_de_sistema(self, superadmin):
        self._quitar_asignacion_directa('auditar_seguridad')

        assert not RbacService.tiene_permiso(superadmin, 'auditar_seguridad')

    def test_un_dueno_no_hereda_nada(self, dueno):
        assert RbacService.permisos_de(dueno).isdisjoint(SISTEMA)

    def test_sin_rol_activo_no_hay_herencia(self, superadmin):
        Rol.objects.get(nombre='SUPERADMIN').desactivar()
        superadmin = type(superadmin).objects.get(pk=superadmin.pk)

        assert not RbacService.es_superadmin(superadmin)
        assert RbacService.permisos_de(superadmin) == frozenset()

    def test_administra_cualquier_complejo(self, superadmin, complejo, complejo_ajeno):
        assert AccesoComplejoService.puede_administrar(superadmin, complejo.id)
        assert AccesoComplejoService.puede_administrar(superadmin, complejo_ajeno.id)
        assert set(AccesoComplejoService.filtrar_queryset(Complejo.objects.all(), superadmin, '')) == {
            complejo, complejo_ajeno,
        }


class TestAccesoAComplejos:
    def test_dueno_solo_administra_los_propios(self, dueno, complejo, complejo_ajeno):
        assert AccesoComplejoService.puede_administrar(dueno, complejo.id)
        assert not AccesoComplejoService.puede_administrar(dueno, complejo_ajeno.id)

    def test_operador_solo_administra_su_complejo_operado(self, operador, complejo, complejo_ajeno):
        assert AccesoComplejoService.puede_administrar(operador, complejo.id)
        assert not AccesoComplejoService.puede_administrar(operador, complejo_ajeno.id)

    def test_operador_sin_complejo_no_administra_ninguno(self, crear_usuario, complejo):
        operador = crear_usuario('libre@talibre.test', 'OPERADOR_COMPLEJO')

        assert not AccesoComplejoService.puede_administrar(operador, complejo.id)
        assert not AccesoComplejoService.filtrar_queryset(Complejo.objects.all(), operador, '').exists()

    def test_jugador_no_administra_complejos(self, jugador, complejo):
        assert not AccesoComplejoService.puede_administrar(jugador, complejo.id)
        assert not AccesoComplejoService.filtrar_queryset(Complejo.objects.all(), jugador, '').exists()

    def test_complejo_dado_de_baja_no_se_administra(self, dueno, operador, complejo):
        complejo.desactivar()

        assert not AccesoComplejoService.puede_administrar(dueno, complejo.id)
        assert not AccesoComplejoService.puede_administrar(operador, complejo.id)

    def test_dueno_suspendido_pierde_el_acceso(self, dueno, complejo):
        dueno.estado = EstadoUsuario.SUSPENDIDO
        dueno.save(update_fields=['estado'])

        assert not AccesoComplejoService.puede_administrar(dueno, complejo.id)

    @pytest.mark.parametrize('valor', [None, '', 'abc', '9999'])
    def test_identificadores_invalidos_o_inexistentes(self, superadmin, valor):
        assert not AccesoComplejoService.puede_administrar(superadmin, valor)

    def test_filtra_recursos_por_ruta_al_complejo(self, dueno, complejo, complejo_ajeno, rbac):
        from core.models import Cobertura, Deporte, Iluminacion, TipoSuperficie

        deporte = Deporte.objects.first()
        datos = {
            'deporte': deporte, 'tipo_superficie': TipoSuperficie.CEMENTO,
            'cobertura': Cobertura.TECHADA, 'iluminacion': Iluminacion.LED, 'precio_base': 1000,
        }
        propia = Cancha.objects.create(complejo=complejo, nombre='Propia', **datos)
        Cancha.objects.create(complejo=complejo_ajeno, nombre='Ajena', **datos)

        visibles = AccesoComplejoService.filtrar_queryset(Cancha.objects.all(), dueno, 'complejo')

        assert list(visibles) == [propia]


class TestClasesDePermiso:
    class _Request:
        def __init__(self, usuario, metodo='GET'):
            self.user = usuario
            self.method = metodo

    def test_vista_sin_declaracion_deniega(self, jugador):
        vista = type('Vista', (), {'get': lambda self: None})()

        assert not TienePermisoRBAC().has_permission(self._Request(jugador), vista)

    def test_head_y_options_usan_los_permisos_de_get(self, jugador):
        vista = type('Vista', (), {
            'permisos_requeridos': {'GET': ('ver_perfil_propio',)},
            'head': lambda self: None,
            'options': lambda self: None,
        })()

        assert TienePermisoRBAC().has_permission(self._Request(jugador, 'HEAD'), vista)
        assert TienePermisoRBAC().has_permission(self._Request(jugador, 'OPTIONS'), vista)

    def test_la_accion_del_viewset_tiene_prioridad(self, jugador):
        vista = type('Vista', (), {
            'action': 'list',
            'permisos_requeridos': {'list': ('auditar_seguridad',), 'GET': ('ver_perfil_propio',)},
            'get': lambda self: None,
        })()

        assert not TienePermisoRBAC().has_permission(self._Request(jugador), vista)

    def test_administra_complejo_sobre_objetos(self, dueno, complejo, complejo_ajeno):
        vista = type('Vista', (), {'campo_complejo': ''})()
        permiso = AdministraComplejo()
        request = self._Request(dueno)

        assert permiso.has_object_permission(request, vista, complejo)
        assert not permiso.has_object_permission(request, vista, complejo_ajeno)
