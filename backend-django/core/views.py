from django.conf import settings
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from .permissions import TienePermisoRBAC
from .serializers import FiltroAuditoriaSerializer, LogAuditoriaSerializer
from .serializers_auth import LoginSerializer, PerfilEdicionSerializer, PerfilSerializer, RegistroSerializer
from .services import AccesoComplejoService, AuditoriaService, SesionService, UsuarioService
from .throttles import LoginRateThrottle, RegistroRateThrottle

NOMBRE_COOKIE_REFRESH = 'refresh'
# El navegador solo envía la cookie a /api/token/, /api/token/refresh/ y /api/token/logout/.
RUTA_COOKIE_REFRESH = '/api/token/'


def _guardar_cookie_refresh(respuesta, refresh):
    respuesta.set_cookie(
        NOMBRE_COOKIE_REFRESH,
        str(refresh),
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=RUTA_COOKIE_REFRESH,
        secure=not settings.DEBUG,
        httponly=True,
        samesite='Strict',
    )


def _borrar_cookie_refresh(respuesta):
    respuesta.delete_cookie(NOMBRE_COOKIE_REFRESH, path=RUTA_COOKIE_REFRESH, samesite='Strict')


class VistaPublica(APIView):
    """
    Sin autenticación por header: un access vencido enviado por el interceptor no debe bloquear
    el login ni el refresh. El header WWW-Authenticate mantiene los rechazos como 401 y no 403.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'


class SaludView(VistaPublica):
    throttle_classes = []

    def get(self, request):
        return Response({'estado': 'ok'})


class RegistroView(VistaPublica):
    throttle_classes = [RegistroRateThrottle]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = UsuarioService.registrar_jugador(serializer.validated_data, AuditoriaService.ip_de_request(request))
        return Response(PerfilSerializer(usuario).data, status=status.HTTP_201_CREATED)


class LoginView(VistaPublica):
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = SesionService.autenticar(
            serializer.validated_data['email'],
            serializer.validated_data['password'],
            AuditoriaService.ip_de_request(request),
        )
        refresh = SesionService.emitir_refresh(usuario)
        respuesta = Response({'access': str(refresh.access_token)})
        _guardar_cookie_refresh(respuesta, refresh)
        return respuesta


class RefreshView(VistaPublica):
    def post(self, request):
        refresh = SesionService.rotar_refresh(request.COOKIES.get(NOMBRE_COOKIE_REFRESH))
        respuesta = Response({'access': str(refresh.access_token)})
        _guardar_cookie_refresh(respuesta, refresh)
        return respuesta


class LogoutView(VistaPublica):
    def post(self, request):
        SesionService.cerrar_sesion(
            request.COOKIES.get(NOMBRE_COOKIE_REFRESH),
            AuditoriaService.ip_de_request(request),
        )
        respuesta = Response(status=status.HTTP_204_NO_CONTENT)
        _borrar_cookie_refresh(respuesta)
        return respuesta


class PerfilView(APIView):
    permission_classes = [TienePermisoRBAC]
    permisos_requeridos = {
        'GET': ('ver_perfil_propio',),
        'PATCH': ('editar_perfil_propio',),
        'DELETE': ('desactivar_perfil_propio',),
    }
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get(self, request):
        return Response(PerfilSerializer(request.user).data)

    def patch(self, request):
        serializer = PerfilEdicionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = UsuarioService.actualizar_perfil(
            request.user, serializer.validated_data, AuditoriaService.ip_de_request(request),
        )
        return Response(PerfilSerializer(usuario).data)

    def delete(self, request):
        UsuarioService.desactivar_cuenta_propia(request.user, AuditoriaService.ip_de_request(request))
        respuesta = Response(status=status.HTTP_204_NO_CONTENT)
        _borrar_cookie_refresh(respuesta)
        return respuesta


class AuditoriaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LogAuditoriaSerializer
    permission_classes = [TienePermisoRBAC]
    permisos_requeridos = {'list': ('auditar_seguridad',)}
    filter_backends = []

    def get_queryset(self):
        filtros = FiltroAuditoriaSerializer(data=self.request.query_params)
        filtros.is_valid(raise_exception=True)
        return AuditoriaService.listar(**filtros.validated_data)


class AccesoComplejoMixin:
    """
    Doble capa para recursos que pertenecen a un complejo:
    - Visibilidad: get_queryset solo devuelve lo administrable, así lo ajeno responde 404.
    - Operación: has_object_permission no corre en un POST, por eso el alta valida el complejo destino
      en perform_create, y la edición que mueve el recurso a otro complejo, en perform_update (403).
    `campo_complejo` es la ruta ORM desde el recurso hasta su complejo, por ejemplo `cancha__complejo`.
    """

    campo_complejo = 'complejo'

    def get_queryset(self):
        return AccesoComplejoService.filtrar_queryset(super().get_queryset(), self.request.user, self.campo_complejo)

    def _complejo_id_destino(self, datos):
        primera, *resto = self.campo_complejo.split('__')
        if primera not in datos:
            return None
        objeto = datos[primera]
        for parte in resto:
            objeto = getattr(objeto, parte, None)
            if objeto is None:
                return None
        return getattr(objeto, 'pk', objeto)

    def perform_create(self, serializer):
        AccesoComplejoService.validar_operacion(
            self.request.user, self._complejo_id_destino(serializer.validated_data),
        )
        serializer.save()

    def perform_update(self, serializer):
        destino = self._complejo_id_destino(serializer.validated_data)
        if destino is not None:
            AccesoComplejoService.validar_operacion(self.request.user, destino)
        serializer.save()
