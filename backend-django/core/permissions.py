from rest_framework.permissions import BasePermission

from .services import AccesoComplejoService, RbacService

METODOS_DE_LECTURA_EQUIVALENTES = {'HEAD': 'GET', 'OPTIONS': 'GET'}


def permisos_requeridos(view, request):
    """
    Lee `permisos_requeridos` de la vista: claves por acción del ViewSet (`list`, `create`...) o por método HTTP.
    Devuelve None si la vista no declara la operación, y en ese caso se deniega.
    """
    declarados = getattr(view, 'permisos_requeridos', None) or {}
    accion = getattr(view, 'action', None)
    if accion and accion in declarados:
        return tuple(declarados[accion])

    metodo = METODOS_DE_LECTURA_EQUIVALENTES.get(request.method, request.method)
    if metodo in declarados:
        return tuple(declarados[metodo])
    return None


class TienePermisoRBAC(BasePermission):
    message = 'No tenés permiso para realizar esta acción.'

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            return False
        # Un método sin handler debe terminar en 405, no en un 403 engañoso.
        if not hasattr(view, request.method.lower()):
            return True
        codigos = permisos_requeridos(view, request)
        if codigos is None:
            return False
        return RbacService.tiene_permisos(usuario, codigos)


def complejo_id_de(obj, campo_complejo):
    """Resuelve el id del complejo de un objeto siguiendo una ruta ORM como `cancha__complejo`."""
    if not campo_complejo:
        return obj.pk
    *intermedios, ultimo = campo_complejo.split('__')
    for parte in intermedios:
        obj = getattr(obj, parte, None)
        if obj is None:
            return None
    return getattr(obj, f'{ultimo}_id', None)


class AdministraComplejo(BasePermission):
    """Segunda barrera sobre objetos ya visibles: el usuario debe administrar el complejo dueño del recurso."""

    message = 'No podés operar sobre recursos de este complejo.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        campo = getattr(view, 'campo_complejo', 'complejo')
        return AccesoComplejoService.puede_administrar(request.user, complejo_id_de(obj, campo))
