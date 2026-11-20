from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework import status

from core.models import (
    EstadoRegistro,
    EstadoUsuario,
    LogAuditoria,
    Permiso,
    Rol,
    RolPermiso,
    TipoEventoAuditoria,
    Usuario,
)
from core.services import MODULOS_EXCLUSIVOS_DE_PLATAFORMA, RbacService

ROLES = '/api/sistema/roles/'
PERMISOS = '/api/sistema/permisos/'
ROLES_BASE = ['SUPERADMIN', 'DUENO_COMPLEJO', 'OPERADOR_COMPLEJO', 'JUGADOR']
CAMPOS_ROL = {
    'id', 'nombre', 'descripcion', 'estado', 'estado_nombre', 'es_base', 'usos', 'permisos',
    'fecha_creacion', 'fecha_modificacion',
}
CAMPOS_PERMISO = {'id', 'codigo', 'nombre', 'modulo', 'asignable'}
PERMISOS_DE_PLATAFORMA = [
    'ver_panel_sistema', 'ver_contratos', 'administrar_contratos', 'ver_usuarios', 'editar_usuarios',
    'desactivar_usuarios', 'administrar_catalogos', 'administrar_roles', 'auditar_seguridad',
]


@pytest.fixture
def api(superadmin, cliente_de):
    return cliente_de(superadmin)


@pytest.fixture
def crear_rol(rbac):
    def _crear(nombre='Encargado de Turno', *codigos, descripcion=''):
        rol = Rol.objects.create(nombre=nombre, descripcion=descripcion)
        for codigo in codigos:
            RolPermiso.objects.create(rol=rol, permiso=Permiso.objects.get(codigo=codigo))
        return rol

    return _crear


@pytest.fixture
def rol_personalizado(crear_rol):
    return crear_rol('Encargado de Turno', 'ver_perfil_propio', 'ver_agenda', descripcion='Atiende el mostrador')


def _id_permiso(codigo):
    return Permiso.objects.get(codigo=codigo).id


def _ids(*codigos):
    return [_id_permiso(codigo) for codigo in codigos]


def _codigos(rol_json):
    return {permiso['codigo'] for permiso in rol_json['permisos']}


def _codigos_activos(rol):
    return set(
        RolPermiso.objects.filter(rol=rol, estado=EstadoRegistro.ACTIVO).values_list('permiso__codigo', flat=True)
    )


def _error(respuesta, campo):
    return str(respuesta.json()['detail'][campo])


def _detalle(rol):
    return f'{ROLES}{rol.id}/'


def _auditoria():
    return LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.CAMBIO_CATALOGO, accion__endswith='de rol')


class TestAcceso:
    def test_anonimo_recibe_401(self, cliente, rbac):
        assert cliente.get(ROLES).status_code == status.HTTP_401_UNAUTHORIZED
        assert cliente.post(ROLES, {'nombre': 'Nuevo'}, format='json').status_code == status.HTTP_401_UNAUTHORIZED
        assert cliente.get(PERMISOS).status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize('fixture_usuario', ['jugador', 'operador', 'dueno'])
    def test_roles_sin_permiso_reciben_403_en_todas_las_operaciones(self, request, cliente_de, rol_personalizado,
                                                                    fixture_usuario):
        api = cliente_de(request.getfixturevalue(fixture_usuario))
        detalle = _detalle(rol_personalizado)

        assert api.get(PERMISOS).status_code == status.HTTP_403_FORBIDDEN
        assert api.get(ROLES).status_code == status.HTTP_403_FORBIDDEN
        assert api.get(detalle).status_code == status.HTTP_403_FORBIDDEN
        assert api.post(ROLES, {'nombre': 'Nuevo'}, format='json').status_code == status.HTTP_403_FORBIDDEN
        assert api.patch(detalle, {'nombre': 'Otro'}, format='json').status_code == status.HTTP_403_FORBIDDEN
        assert api.delete(detalle).status_code == status.HTTP_403_FORBIDDEN
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.nombre == 'Encargado de Turno'
        assert rol_personalizado.estado == EstadoRegistro.ACTIVO
        assert Rol.objects.count() == len(ROLES_BASE) + 1

    def test_el_rechazo_por_rol_queda_en_auditoria_de_acceso(self, jugador, cliente_de):
        cliente_de(jugador).post(ROLES, {'nombre': 'Nuevo'}, format='json')

        assert LogAuditoria.objects.filter(tipo_evento=TipoEventoAuditoria.ACCESO_DENEGADO).exists()
        assert not _auditoria().exists()

    def test_solo_el_superadmin_tiene_el_permiso(self, rbac):
        asignados = set(
            RolPermiso.objects.filter(permiso__codigo='administrar_roles', estado=EstadoRegistro.ACTIVO)
            .values_list('rol__nombre', flat=True)
        )

        assert asignados == {'SUPERADMIN'}

    def test_la_ruta_no_acepta_put_ni_post_en_el_detalle(self, api, rol_personalizado):
        assert api.put(_detalle(rol_personalizado), {'nombre': 'Otro'}, format='json').status_code == 405
        assert api.post(_detalle(rol_personalizado), {'nombre': 'Otro'}, format='json').status_code == 405

    def test_el_catalogo_de_permisos_es_de_solo_lectura(self, api):
        assert api.post(PERMISOS, {'codigo': 'nuevo'}, format='json').status_code == 405
        assert api.delete(PERMISOS).status_code == 405


class TestCatalogoDePermisos:
    def test_lista_todos_los_permisos_activos_sin_paginar(self, api):
        respuesta = api.get(PERMISOS)

        assert respuesta.status_code == status.HTTP_200_OK
        assert isinstance(respuesta.json(), list)
        assert len(respuesta.json()) == Permiso.objects.filter(estado=EstadoRegistro.ACTIVO).count()
        assert set(respuesta.json()[0]) == CAMPOS_PERMISO

    def test_marca_como_no_asignables_los_de_la_plataforma(self, api):
        por_codigo = {permiso['codigo']: permiso for permiso in api.get(PERMISOS).json()}

        for codigo, permiso in por_codigo.items():
            assert permiso['asignable'] is (permiso['modulo'] not in MODULOS_EXCLUSIVOS_DE_PLATAFORMA)
        assert {codigo for codigo, permiso in por_codigo.items() if not permiso['asignable']} == set(
            PERMISOS_DE_PLATAFORMA
        )
        assert por_codigo['ver_agenda']['asignable'] is True

    def test_omite_los_permisos_dados_de_baja(self, api):
        Permiso.objects.get(codigo='ver_agenda').desactivar()

        codigos = {permiso['codigo'] for permiso in api.get(PERMISOS).json()}

        assert 'ver_agenda' not in codigos
        assert 'ver_canchas' in codigos


class TestListadoYDetalle:
    def test_lista_los_roles_base_sin_paginar_y_marcados_como_protegidos(self, api):
        respuesta = api.get(ROLES)

        assert respuesta.status_code == status.HTTP_200_OK
        assert isinstance(respuesta.json(), list)
        assert {rol['nombre'] for rol in respuesta.json()} == set(ROLES_BASE)
        assert all(rol['es_base'] is True for rol in respuesta.json())
        assert set(respuesta.json()[0]) == CAMPOS_ROL

    def test_cada_rol_base_informa_sus_permisos_reales(self, api):
        por_nombre = {rol['nombre']: rol for rol in api.get(ROLES).json()}

        assert len(por_nombre['SUPERADMIN']['permisos']) == Permiso.objects.count()
        assert 'configurar_complejo' in _codigos(por_nombre['DUENO_COMPLEJO'])
        assert 'configurar_complejo' not in _codigos(por_nombre['OPERADOR_COMPLEJO'])
        assert 'reservar_turno' in _codigos(por_nombre['JUGADOR'])
        assert set(por_nombre['JUGADOR']['permisos'][0]) == {'id', 'codigo', 'nombre', 'modulo'}

    def test_un_rol_personalizado_no_es_base_y_lleva_sus_datos(self, api, rol_personalizado):
        respuesta = api.get(_detalle(rol_personalizado))

        assert respuesta.status_code == status.HTTP_200_OK
        cuerpo = respuesta.json()
        assert cuerpo['es_base'] is False
        assert cuerpo['nombre'] == 'Encargado de Turno'
        assert cuerpo['descripcion'] == 'Atiende el mostrador'
        assert cuerpo['estado'] == EstadoRegistro.ACTIVO
        assert cuerpo['estado_nombre'] == 'Activo'
        assert cuerpo['usos'] == 0
        assert _codigos(cuerpo) == {'ver_perfil_propio', 'ver_agenda'}

    def test_cuenta_los_usuarios_vigentes_y_no_las_bajas(self, api, rol_personalizado, crear_usuario):
        for correo, estado in (
            ('activo@talibre.test', EstadoUsuario.ACTIVO),
            ('suspendido@talibre.test', EstadoUsuario.SUSPENDIDO),
            ('baja@talibre.test', EstadoUsuario.BAJA),
        ):
            usuario = crear_usuario(correo, 'JUGADOR', estado=estado)
            Usuario.objects.filter(pk=usuario.pk).update(rol=rol_personalizado)

        assert api.get(_detalle(rol_personalizado)).json()['usos'] == 2

    def test_incluye_los_roles_dados_de_baja(self, api, rol_personalizado):
        rol_personalizado.desactivar()

        por_nombre = {rol['nombre']: rol for rol in api.get(ROLES).json()}

        assert por_nombre['Encargado de Turno']['estado'] == EstadoRegistro.BAJA
        assert por_nombre['Encargado de Turno']['estado_nombre'] == 'Baja lógica'

    def test_omite_las_asignaciones_dadas_de_baja(self, api, rol_personalizado):
        RolPermiso.objects.get(rol=rol_personalizado, permiso__codigo='ver_agenda').desactivar()

        assert _codigos(api.get(_detalle(rol_personalizado)).json()) == {'ver_perfil_propio'}

    def test_detalle_inexistente_responde_404(self, api, rbac):
        assert api.get(f'{ROLES}999999/').status_code == status.HTTP_404_NOT_FOUND


class TestAlta:
    def test_crea_un_rol_con_sus_permisos(self, api, superadmin):
        respuesta = api.post(ROLES, {
            'nombre': 'Encargado de Turno', 'descripcion': 'Atiende el mostrador',
            'permisos': _ids('ver_perfil_propio', 'ver_agenda'),
        }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        cuerpo = respuesta.json()
        assert set(cuerpo) == CAMPOS_ROL
        assert cuerpo['es_base'] is False
        assert cuerpo['usos'] == 0
        assert _codigos(cuerpo) == {'ver_perfil_propio', 'ver_agenda'}
        assert Rol.objects.get(id=cuerpo['id']).estado == EstadoRegistro.ACTIVO

    def test_sin_permisos_ni_descripcion_crea_un_rol_vacio(self, api):
        respuesta = api.post(ROLES, {'nombre': 'Observador'}, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['permisos'] == []
        assert respuesta.json()['descripcion'] == ''

    def test_limpia_etiquetas_y_espacios_del_nombre_y_la_descripcion(self, api):
        respuesta = api.post(ROLES, {
            'nombre': '  <b>Encargado</b>   de   <script>alert(1)</script>Turno ',
            'descripcion': '<img src=x onerror=alert(1)>Mostrador',
        }, format='json')

        assert respuesta.status_code == status.HTTP_201_CREATED
        assert respuesta.json()['nombre'] == 'Encargado de Turno'
        assert respuesta.json()['descripcion'] == 'Mostrador'

    @pytest.mark.parametrize('nombre', [
        'encargado de turno', 'ENCARGADO DE TURNO', 'Encargado  de  Turno', 'EncargadoDeTurno',
        'encargado_de_turno', ' Encargado de Turno ',
    ])
    def test_rechaza_un_nombre_repetido_sin_distinguir_mayusculas_ni_espacios(self, api, rol_personalizado, nombre):
        respuesta = api.post(ROLES, {'nombre': nombre}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'nombre' in respuesta.json()['detail']
        assert Rol.objects.count() == len(ROLES_BASE) + 1

    @pytest.mark.parametrize('nombre', ['superadmin', 'Super Admin', 'jugador', 'Dueno_Complejo', 'operador complejo'])
    def test_rechaza_nombres_que_se_confunden_con_un_rol_base(self, api, rbac, nombre):
        respuesta = api.post(ROLES, {'nombre': nombre}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'nombre' in respuesta.json()['detail']
        assert Rol.objects.count() == len(ROLES_BASE)

    def test_un_nombre_de_rol_dado_de_baja_sigue_ocupado(self, api, rol_personalizado):
        rol_personalizado.desactivar()

        respuesta = api.post(ROLES, {'nombre': 'encargado de turno'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'dado de baja' in _error(respuesta, 'nombre')

    @pytest.mark.parametrize('cuerpo', [
        {}, {'nombre': ''}, {'nombre': '   '}, {'nombre': 'A'}, {'nombre': 'x' * 51},
        {'nombre': 'Valido', 'descripcion': 'x' * 151}, {'nombre': '<b></b>'},
    ])
    def test_valida_el_nombre_y_la_descripcion(self, api, rbac, cuerpo):
        respuesta = api.post(ROLES, cuerpo, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert Rol.objects.count() == len(ROLES_BASE)

    def test_rechaza_permisos_inexistentes_y_no_crea_nada(self, api, rbac):
        respuesta = api.post(ROLES, {'nombre': 'Nuevo', 'permisos': [*_ids('ver_agenda'), 999999]}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert '999999' in _error(respuesta, 'permisos')
        assert not Rol.objects.filter(nombre='Nuevo').exists()
        assert not _auditoria().exists()

    def test_rechaza_un_permiso_dado_de_baja(self, api, rbac):
        Permiso.objects.get(codigo='ver_agenda').desactivar()

        respuesta = api.post(ROLES, {'nombre': 'Nuevo', 'permisos': _ids('ver_agenda')}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert not Rol.objects.filter(nombre='Nuevo').exists()

    def test_rechaza_permisos_repetidos(self, api, rbac):
        respuesta = api.post(ROLES, {'nombre': 'Nuevo', 'permisos': _ids('ver_agenda', 'ver_agenda')}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'No repitas' in _error(respuesta, 'permisos')
        assert not Rol.objects.filter(nombre='Nuevo').exists()

    @pytest.mark.parametrize('permisos', ['ver_agenda', [None], ['ver_agenda'], [0], [-3], [1.5]])
    def test_rechaza_permisos_con_formato_invalido(self, api, rbac, permisos):
        respuesta = api.post(ROLES, {'nombre': 'Nuevo', 'permisos': permisos}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert not Rol.objects.filter(nombre='Nuevo').exists()

    @pytest.mark.parametrize('codigo', PERMISOS_DE_PLATAFORMA)
    def test_no_permite_la_escalacion_con_permisos_de_la_plataforma(self, api, rbac, codigo):
        respuesta = api.post(ROLES, {'nombre': 'Nuevo', 'permisos': _ids('ver_agenda', codigo)}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert codigo in _error(respuesta, 'permisos')
        assert not Rol.objects.filter(nombre='Nuevo').exists()
        assert not RolPermiso.objects.exclude(rol__nombre__in=ROLES_BASE).exists()

    def test_queda_registrado_en_la_auditoria(self, api, superadmin):
        respuesta = api.post(ROLES, {'nombre': 'Encargado', 'permisos': _ids('ver_agenda', 'ver_canchas')}, format='json')

        log = _auditoria().get()
        assert log.accion == 'Alta de rol'
        assert log.usuario_id == superadmin.id
        assert f'id {respuesta.json()["id"]}' in log.detalle
        assert '«Encargado»' in log.detalle
        assert 'ver_agenda, ver_canchas' in log.detalle


class TestEdicion:
    def test_renombra_y_cambia_la_descripcion(self, api, rol_personalizado, superadmin):
        respuesta = api.patch(
            _detalle(rol_personalizado), {'nombre': 'Encargado General', 'descripcion': 'Nueva'}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['nombre'] == 'Encargado General'
        assert respuesta.json()['descripcion'] == 'Nueva'
        assert _codigos(respuesta.json()) == {'ver_perfil_propio', 'ver_agenda'}
        log = _auditoria().get()
        assert log.accion == 'Modificación de rol'
        assert log.usuario_id == superadmin.id
        assert 'Antes: «Encargado de Turno»' in log.detalle
        assert 'Descripción modificada' in log.detalle

    def test_puede_cambiar_solo_la_capitalizacion_de_su_propio_nombre(self, api, rol_personalizado):
        respuesta = api.patch(_detalle(rol_personalizado), {'nombre': 'ENCARGADO DE TURNO'}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['nombre'] == 'ENCARGADO DE TURNO'

    def test_reemplaza_los_permisos_y_los_quitados_quedan_con_baja_logica(self, api, rol_personalizado):
        respuesta = api.patch(
            _detalle(rol_personalizado), {'permisos': _ids('ver_perfil_propio', 'ver_canchas')}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert _codigos(respuesta.json()) == {'ver_perfil_propio', 'ver_canchas'}
        quitada = RolPermiso.objects.get(rol=rol_personalizado, permiso__codigo='ver_agenda')
        assert quitada.estado == EstadoRegistro.BAJA
        log = _auditoria().get()
        assert 'Permisos agregados: ver_canchas.' in log.detalle
        assert 'Permisos quitados: ver_agenda.' in log.detalle

    def test_volver_a_asignar_un_permiso_quitado_reactiva_la_fila(self, api, rol_personalizado):
        api.patch(_detalle(rol_personalizado), {'permisos': _ids('ver_perfil_propio')}, format='json')

        respuesta = api.patch(
            _detalle(rol_personalizado), {'permisos': _ids('ver_perfil_propio', 'ver_agenda')}, format='json',
        )

        assert _codigos(respuesta.json()) == {'ver_perfil_propio', 'ver_agenda'}
        assert RolPermiso.objects.filter(rol=rol_personalizado, permiso__codigo='ver_agenda').count() == 1

    def test_una_lista_vacia_quita_todos_los_permisos(self, api, rol_personalizado):
        respuesta = api.patch(_detalle(rol_personalizado), {'permisos': []}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['permisos'] == []
        assert _codigos_activos(rol_personalizado) == set()

    def test_omitir_permisos_los_deja_como_estaban(self, api, rol_personalizado):
        api.patch(_detalle(rol_personalizado), {'nombre': 'Otro Nombre'}, format='json')

        assert _codigos_activos(rol_personalizado) == {'ver_perfil_propio', 'ver_agenda'}

    def test_rechaza_el_nombre_de_otro_rol(self, api, rol_personalizado, crear_rol):
        crear_rol('Cajero')

        respuesta = api.patch(_detalle(rol_personalizado), {'nombre': 'cajero'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'nombre' in respuesta.json()['detail']
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.nombre == 'Encargado de Turno'

    def test_rechaza_renombrarlo_como_un_rol_base(self, api, rol_personalizado):
        respuesta = api.patch(_detalle(rol_personalizado), {'nombre': 'Super Admin'}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.nombre == 'Encargado de Turno'

    @pytest.mark.parametrize('codigo', PERMISOS_DE_PLATAFORMA)
    def test_no_permite_agregar_permisos_de_la_plataforma(self, api, rol_personalizado, codigo):
        respuesta = api.patch(
            _detalle(rol_personalizado), {'permisos': _ids('ver_agenda', codigo)}, format='json',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert codigo in _error(respuesta, 'permisos')
        assert _codigos_activos(rol_personalizado) == {'ver_perfil_propio', 'ver_agenda'}
        assert not _auditoria().exists()

    def test_un_error_de_permisos_no_aplica_el_cambio_de_nombre(self, api, rol_personalizado):
        respuesta = api.patch(
            _detalle(rol_personalizado), {'nombre': 'Otro Nombre', 'permisos': [999999]}, format='json',
        )

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.nombre == 'Encargado de Turno'

    def test_rechaza_permisos_inexistentes_y_repetidos(self, api, rol_personalizado):
        assert api.patch(_detalle(rol_personalizado), {'permisos': [999999]}, format='json').status_code == 400
        repetidos = _ids('ver_agenda', 'ver_agenda')
        assert api.patch(_detalle(rol_personalizado), {'permisos': repetidos}, format='json').status_code == 400
        assert _codigos_activos(rol_personalizado) == {'ver_perfil_propio', 'ver_agenda'}

    def test_un_cuerpo_sin_campos_se_rechaza(self, api, rol_personalizado):
        assert api.patch(_detalle(rol_personalizado), {}, format='json').status_code == status.HTTP_400_BAD_REQUEST

    def test_un_cambio_nulo_no_audita(self, api, rol_personalizado):
        respuesta = api.patch(
            _detalle(rol_personalizado),
            {'nombre': 'Encargado de Turno', 'permisos': _ids('ver_perfil_propio', 'ver_agenda')}, format='json',
        )

        assert respuesta.status_code == status.HTTP_200_OK
        assert not _auditoria().exists()

    def test_reactiva_un_rol_dado_de_baja(self, api, rol_personalizado):
        rol_personalizado.desactivar()

        respuesta = api.patch(_detalle(rol_personalizado), {'estado': EstadoRegistro.ACTIVO}, format='json')

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json()['estado'] == EstadoRegistro.ACTIVO
        assert 'Reactivado' in _auditoria().get().detalle

    @pytest.mark.parametrize('estado', [EstadoRegistro.BAJA, 2, 'x'])
    def test_el_estado_solo_admite_reactivar(self, api, rol_personalizado, estado):
        respuesta = api.patch(_detalle(rol_personalizado), {'estado': estado}, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.estado == EstadoRegistro.ACTIVO

    def test_editar_un_rol_inexistente_responde_404(self, api, rbac):
        assert api.patch(f'{ROLES}999999/', {'nombre': 'Otro'}, format='json').status_code == 404


class TestBaja:
    def test_da_de_baja_un_rol_sin_usuarios_y_conserva_sus_asignaciones(self, api, rol_personalizado, superadmin):
        respuesta = api.delete(_detalle(rol_personalizado))

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.estado == EstadoRegistro.BAJA
        assert _codigos_activos(rol_personalizado) == {'ver_perfil_propio', 'ver_agenda'}
        log = _auditoria().get()
        assert log.accion == 'Baja de rol'
        assert log.usuario_id == superadmin.id
        assert f'id {rol_personalizado.id}' in log.detalle

    def test_sigue_listado_y_ya_no_es_asignable_a_usuarios(self, api, rol_personalizado, jugador):
        api.delete(_detalle(rol_personalizado))

        assert api.get(_detalle(rol_personalizado)).json()['estado'] == EstadoRegistro.BAJA
        asignacion = api.patch(f'/api/usuarios/{jugador.id}/', {'rol': 'Encargado de Turno'}, format='json')
        assert asignacion.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize('estado', [EstadoUsuario.ACTIVO, EstadoUsuario.SUSPENDIDO])
    def test_rechaza_la_baja_si_lo_usa_una_cuenta_vigente(self, api, rol_personalizado, jugador, estado):
        Usuario.objects.filter(pk=jugador.pk).update(rol=rol_personalizado, estado=estado)

        respuesta = api.delete(_detalle(rol_personalizado))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'lo usa 1 usuario' in respuesta.json()['detail']
        assert 'Encargado de Turno' in respuesta.json()['detail']
        rol_personalizado.refresh_from_db()
        assert rol_personalizado.estado == EstadoRegistro.ACTIVO
        assert not _auditoria().exists()

    def test_el_mensaje_cuenta_los_usuarios(self, api, rol_personalizado, crear_usuario):
        for numero in range(3):
            crear_usuario(f'usuario{numero}@talibre.test')
        Usuario.objects.exclude(rol__nombre='SUPERADMIN').update(rol=rol_personalizado)

        respuesta = api.delete(_detalle(rol_personalizado))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'lo usan 3 usuarios' in respuesta.json()['detail']

    def test_las_cuentas_dadas_de_baja_no_impiden_la_baja_del_rol(self, api, rol_personalizado, jugador):
        Usuario.objects.filter(pk=jugador.pk).update(rol=rol_personalizado, estado=EstadoUsuario.BAJA)

        assert api.delete(_detalle(rol_personalizado)).status_code == status.HTTP_204_NO_CONTENT

    def test_rechaza_dar_de_baja_dos_veces(self, api, rol_personalizado):
        api.delete(_detalle(rol_personalizado))

        respuesta = api.delete(_detalle(rol_personalizado))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ya está dado de baja' in respuesta.json()['detail']
        assert _auditoria().count() == 1

    def test_la_baja_nunca_borra_filas(self, api, rol_personalizado):
        api.delete(_detalle(rol_personalizado))

        assert Rol.objects.filter(id=rol_personalizado.id).exists()
        assert RolPermiso.objects.filter(rol=rol_personalizado).count() == 2

    def test_baja_de_un_rol_inexistente_responde_404(self, api, rbac):
        assert api.delete(f'{ROLES}999999/').status_code == status.HTTP_404_NOT_FOUND


class TestProteccionDeRolesBase:
    @pytest.mark.parametrize('nombre', ROLES_BASE)
    def test_no_se_puede_dar_de_baja(self, api, rbac, nombre):
        rol = Rol.objects.get(nombre=nombre)

        respuesta = api.delete(_detalle(rol))

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'rol base del sistema' in respuesta.json()['detail']
        rol.refresh_from_db()
        assert rol.estado == EstadoRegistro.ACTIVO
        assert not _auditoria().exists()

    @pytest.mark.parametrize('nombre', ROLES_BASE)
    @pytest.mark.parametrize('cuerpo', [
        {'nombre': 'Renombrado'}, {'descripcion': 'Otra'}, {'permisos': []}, {'estado': EstadoRegistro.ACTIVO},
    ])
    def test_no_se_puede_modificar_ni_renombrar_ni_cambiar_sus_permisos(self, api, rbac, nombre, cuerpo):
        rol = Rol.objects.get(nombre=nombre)
        permisos_antes = _codigos_activos(rol)
        descripcion = rol.descripcion

        respuesta = api.patch(_detalle(rol), cuerpo, format='json')

        assert respuesta.status_code == status.HTTP_400_BAD_REQUEST
        assert 'rol base del sistema' in respuesta.json()['detail']
        rol.refresh_from_db()
        assert rol.nombre == nombre
        assert rol.descripcion == descripcion
        assert _codigos_activos(rol) == permisos_antes
        assert not _auditoria().exists()

    def test_el_superadmin_conserva_todos_sus_permisos_incluso_tras_intentar_quitarlos(self, api, superadmin):
        rol = Rol.objects.get(nombre='SUPERADMIN')

        api.patch(_detalle(rol), {'permisos': []}, format='json')

        assert RbacService.tiene_permiso(superadmin, 'administrar_roles')
        assert api.get(ROLES).status_code == status.HTTP_200_OK

    def test_un_rol_personalizado_no_puede_tomar_el_nombre_de_un_base_ni_siquiera_en_el_alta(self, api, rbac):
        assert api.post(ROLES, {'nombre': 'SUPERADMIN'}, format='json').status_code == status.HTTP_400_BAD_REQUEST
        assert Rol.objects.filter(nombre__iexact='superadmin').count() == 1


class TestEfectoSobreLosPermisos:
    def test_un_usuario_con_rol_personalizado_recibe_exactamente_sus_permisos(self, api, rol_personalizado, crear_usuario):
        usuario = crear_usuario('encargado@talibre.test', 'JUGADOR')
        Usuario.objects.filter(pk=usuario.pk).update(rol=rol_personalizado)

        assert RbacService.permisos_de(Usuario.objects.get(pk=usuario.pk)) == {'ver_perfil_propio', 'ver_agenda'}

    def test_cambiar_los_permisos_del_rol_se_aplica_en_la_siguiente_consulta(self, api, rol_personalizado, crear_usuario):
        usuario = crear_usuario('encargado@talibre.test', 'JUGADOR')
        Usuario.objects.filter(pk=usuario.pk).update(rol=rol_personalizado)

        api.patch(_detalle(rol_personalizado), {'permisos': _ids('ver_canchas')}, format='json')

        assert RbacService.permisos_de(Usuario.objects.get(pk=usuario.pk)) == {'ver_canchas'}

    def test_un_rol_personalizado_no_otorga_acceso_a_los_endpoints_de_sistema(self, api, crear_rol, crear_usuario,
                                                                              cliente_de):
        rol = crear_rol('Auditor Externo', 'ver_perfil_propio')
        usuario = crear_usuario('auditor@talibre.test', 'JUGADOR')
        Usuario.objects.filter(pk=usuario.pk).update(rol=rol)
        propio = cliente_de(Usuario.objects.get(pk=usuario.pk))

        assert propio.get(ROLES).status_code == status.HTTP_403_FORBIDDEN
        assert propio.get(PERMISOS).status_code == status.HTTP_403_FORBIDDEN
        assert propio.get('/api/sistema/deportes/').status_code == status.HTTP_403_FORBIDDEN


class TestCargaInicial:
    def test_repetir_seed_inicial_no_toca_los_roles_personalizados(self, api, rol_personalizado):
        api.patch(_detalle(rol_personalizado), {'permisos': _ids('ver_canchas')}, format='json')

        call_command('seed_inicial', '--sin-demo', stdout=StringIO())

        rol_personalizado.refresh_from_db()
        assert rol_personalizado.estado == EstadoRegistro.ACTIVO
        assert _codigos_activos(rol_personalizado) == {'ver_canchas'}

    def test_el_seed_deja_a_los_roles_base_con_el_permiso_de_administrar_roles_solo_en_superadmin(self, api):
        call_command('seed_inicial', '--sin-demo', stdout=StringIO())

        por_nombre = {rol['nombre']: rol for rol in api.get(ROLES).json()}

        assert 'administrar_roles' in _codigos(por_nombre['SUPERADMIN'])
        assert all(
            'administrar_roles' not in _codigos(rol) for nombre, rol in por_nombre.items() if nombre != 'SUPERADMIN'
        )
