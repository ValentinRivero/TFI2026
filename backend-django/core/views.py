from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from .filters import (
    AgendaFilter,
    BusquedaFlexibleFilter,
    CanchaFilter,
    CatalogoComplejoFilter,
    ContratoFilter,
    ExcepcionHorariaFilter,
    HorarioAperturaFilter,
    ReservaPropiaFilter,
    TurnoFijoFilter,
    UsuarioFilter,
)
from .permissions import AdministraComplejo, TienePermisoRBAC
from .serializers import (
    CanchaSerializer,
    CatalogoMaestroSerializer,
    ComplejoAdminSerializer,
    ComplejoCatalogoSerializer,
    ComplejoConfiguracionSerializer,
    ComplejoDetallePublicoSerializer,
    ConfirmacionSerializer,
    ContratoAltaSerializer,
    ContratoEstadoSerializer,
    ContratoSerializer,
    ExcepcionHorariaSerializer,
    FechaTurnoFijoSerializer,
    FiltroAuditoriaSerializer,
    FiltroGrillaSerializer,
    GrillaSerializer,
    HorarioAperturaSerializer,
    LogAuditoriaSerializer,
    OperadorSerializer,
    ReaperturaSerializer,
    ReservaAgendaEdicionSerializer,
    ReservaAgendaSerializer,
    ReservaAltaSerializer,
    ReservaManualSerializer,
    ReservaPropiaSerializer,
    ServiciosComplejoSerializer,
    TurnoFijoSerializer,
    UsuarioAdminEdicionSerializer,
    UsuarioAdminSerializer,
    VincularOperadorSerializer,
)
from .serializers_auth import LoginSerializer, PerfilEdicionSerializer, PerfilSerializer, RegistroSerializer
from .services import (
    AccesoComplejoService,
    AuditoriaService,
    BajaDeCuentaService,
    CanchaService,
    CatalogoService,
    ComplejoService,
    ContratoService,
    ExcepcionHorariaService,
    GrillaService,
    HorarioAperturaService,
    OperadorService,
    RbacService,
    ReservaService,
    SesionService,
    TurnoFijoService,
    UsuarioAdminService,
    UsuarioService,
)
from .throttles import LoginRateThrottle, RegistroRateThrottle, ReservaRateThrottle

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


class PerfilBajaView(APIView):
    """Vista previa de la baja propia: qué reservas y turnos fijos se cancelan y cuáles se conservan."""

    permission_classes = [TienePermisoRBAC]
    permisos_requeridos = {'GET': ('desactivar_perfil_propio',)}
    http_method_names = ['get', 'head', 'options']

    def get(self, request):
        return Response(BajaDeCuentaService.vista_previa(request.user))


def _confirmado(request):
    """`confirmar` llega en el cuerpo (PATCH) o en la query string (DELETE, que no suele llevar cuerpo)."""
    valor = request.data.get('confirmar') if hasattr(request.data, 'get') else None
    if valor is None:
        valor = request.query_params.get('confirmar')
    entrada = ConfirmacionSerializer(data={} if valor is None else {'confirmar': valor})
    entrada.is_valid(raise_exception=True)
    return entrada.validated_data['confirmar']


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
        self.guardar(serializer)

    def perform_update(self, serializer):
        destino = self._complejo_id_destino(serializer.validated_data)
        if destino is not None:
            AccesoComplejoService.validar_operacion(self.request.user, destino)
        self.guardar(serializer)

    def guardar(self, serializer):
        """Persiste el alta o la edición ya autorizada; las vistas de dominio delegan aquí en su servicio."""
        serializer.save()


class PermisosPorCampoMixin:
    """
    Algunos campos exigen un permiso además del de la acción (por ejemplo, los precios). Se exige solo
    cuando el valor enviado cambia el vigente; en un alta, cuando se informa un valor.
    """

    permisos_por_campo = {}

    def validar_permisos_por_campo(self, datos, instancia=None):
        for campo, codigo in self.permisos_por_campo.items():
            if campo not in datos:
                continue
            actual = getattr(instancia, campo) if instancia is not None else None
            if datos[campo] != actual and not RbacService.tiene_permiso(self.request.user, codigo):
                raise PermissionDenied(f'No tenés permiso para modificar el campo {campo}.')


class AccionesPublicasMixin:
    """
    Las acciones públicas ignoran el header Authorization, como VistaPublica: un access vencido enviado
    por el interceptor no debe bloquear la consulta del catálogo.
    """

    acciones_publicas = frozenset()

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        if self.action in self.acciones_publicas:
            request.authenticators = ()
        return request

    def get_permissions(self):
        if self.action in self.acciones_publicas:
            return [AllowAny()]
        return super().get_permissions()


class CatalogoMaestroViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CatalogoMaestroSerializer
    # Catálogos maestros chicos y acotados que administra la plataforma (unas pocas filas): van completos.
    pagination_class = None
    filter_backends = []


class DeporteViewSet(CatalogoMaestroViewSet):
    def get_queryset(self):
        return CatalogoService.deportes()


class ServicioViewSet(CatalogoMaestroViewSet):
    def get_queryset(self):
        return CatalogoService.servicios()


BACKENDS_DE_LISTADO = (DjangoFilterBackend, BusquedaFlexibleFilter, OrderingFilter)


class ComplejoViewSet(AccionesPublicasMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    """
    Catálogo público (list, retrieve) y administración del complejo sobre la misma ruta. Lo público solo ve
    contratos activos; lo administrativo, los complejos que el usuario administra (lo ajeno responde 404).
    """

    acciones_publicas = frozenset({'list', 'retrieve', 'grilla'})
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'administrados': ('ver_panel_complejo',),
        'partial_update': ('configurar_complejo',),
        'servicios': ('configurar_complejo',),
        'operadores': ('ver_operadores',),
        'agregar_operador': ('gestionar_operadores',),
        'quitar_operador': ('gestionar_operadores',),
    }
    campo_complejo = ''
    lookup_value_regex = r'\d+'
    filterset_class = CatalogoComplejoFilter
    search_fields = ('nombre', 'direccion')
    ordering_fields = ('nombre', 'precio_desde')
    ordering = ('nombre', 'id')

    @property
    def filter_backends(self):
        return BACKENDS_DE_LISTADO if self.action == 'list' else ()

    def get_queryset(self):
        if self.action in self.acciones_publicas:
            return CatalogoService.complejos_publicos()
        return ComplejoService.listar_administrables(self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return ComplejoCatalogoSerializer
        if self.action == 'retrieve':
            return ComplejoDetallePublicoSerializer
        return ComplejoAdminSerializer

    def _respuesta_paginada(self, queryset, serializer_class):
        pagina = self.paginate_queryset(queryset)
        return self.get_paginated_response(serializer_class(pagina, many=True).data)

    def partial_update(self, request, pk=None):
        complejo = self.get_object()
        entrada = ComplejoConfiguracionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        complejo = ComplejoService.actualizar_configuracion(
            complejo, entrada.validated_data, request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(ComplejoAdminSerializer(complejo).data)

    # La grilla de un día está acotada por las canchas del complejo y sus rangos horarios: va completa.
    @action(detail=True, methods=['get'], pagination_class=None)
    def grilla(self, request, pk=None):
        entrada = FiltroGrillaSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        grilla = GrillaService.calcular(int(pk), entrada.validated_data['fecha'])
        return Response(GrillaSerializer(grilla).data)

    @action(detail=False, methods=['get'])
    def administrados(self, request):
        return self._respuesta_paginada(self.get_queryset(), ComplejoAdminSerializer)

    @action(detail=True, methods=['put'])
    def servicios(self, request, pk=None):
        complejo = self.get_object()
        entrada = ServiciosComplejoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        servicios = ComplejoService.sincronizar_servicios(
            complejo, entrada.validated_data['servicios'], request.user, AuditoriaService.ip_de_request(request),
        )
        return Response({'servicios': CatalogoMaestroSerializer(servicios, many=True).data})

    @action(detail=True, methods=['get'])
    def operadores(self, request, pk=None):
        complejo = self.get_object()
        return self._respuesta_paginada(OperadorService.listar(complejo), OperadorSerializer)

    @operadores.mapping.post
    def agregar_operador(self, request, pk=None):
        complejo = self.get_object()
        entrada = VincularOperadorSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        operador = OperadorService.vincular(
            complejo, entrada.validated_data['email'], request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(OperadorSerializer(operador).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'operadores/(?P<usuario_id>\d+)')
    def quitar_operador(self, request, pk=None, usuario_id=None):
        complejo = self.get_object()
        OperadorService.desvincular(complejo, int(usuario_id), request.user, AuditoriaService.ip_de_request(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CanchaViewSet(PermisosPorCampoMixin, AccesoComplejoMixin, viewsets.ModelViewSet):
    serializer_class = CanchaSerializer
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'list': ('ver_canchas',),
        'retrieve': ('ver_canchas',),
        'create': ('administrar_canchas',),
        'partial_update': ('administrar_canchas',),
        'destroy': ('administrar_canchas',),
    }
    # Un alta fija el precio igual que una edición: si no se exigiera también en el alta, dar de baja y
    # volver a crear la cancha alcanzaría para cambiar el precio sin el permiso.
    permisos_por_campo = {'precio_base': 'administrar_precios'}
    lookup_value_regex = r'\d+'
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    queryset = CanchaService.listar()
    filterset_class = CanchaFilter
    ordering_fields = ('nombre', 'precio_base', 'id')
    ordering = ('complejo_id', 'nombre', 'id')
    filter_backends = BACKENDS_DE_LISTADO

    def list(self, request, *args, **kwargs):
        complejo_id = request.query_params.get('complejo', '')
        if complejo_id.isdigit() and not AccesoComplejoService.puede_administrar(request.user, complejo_id):
            raise NotFound()
        return super().list(request, *args, **kwargs)

    def guardar(self, serializer):
        self.validar_permisos_por_campo(serializer.validated_data, serializer.instance)
        if serializer.instance is None:
            serializer.instance = CanchaService.crear(serializer.validated_data)
        else:
            serializer.instance = CanchaService.actualizar(
                serializer.instance, serializer.validated_data, _confirmado(self.request),
                self.request.user, AuditoriaService.ip_de_request(self.request),
            )

    def perform_destroy(self, instance):
        CanchaService.dar_de_baja(instance)


class HorarioAperturaViewSet(PermisosPorCampoMixin, AccesoComplejoMixin, viewsets.ModelViewSet):
    serializer_class = HorarioAperturaSerializer
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'list': ('ver_canchas',),
        'retrieve': ('ver_canchas',),
        'create': ('administrar_horarios',),
        'partial_update': ('administrar_horarios',),
        'destroy': ('administrar_horarios',),
    }
    permisos_por_campo = {'precio_diferenciado': 'administrar_precios'}
    campo_complejo = 'cancha__complejo'
    lookup_value_regex = r'\d+'
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    queryset = HorarioAperturaService.listar()
    filterset_class = HorarioAperturaFilter
    ordering_fields = ('dia_semana', 'hora_apertura', 'id')
    ordering = ('cancha_id', 'dia_semana', 'id')
    filter_backends = BACKENDS_DE_LISTADO

    def list(self, request, *args, **kwargs):
        cancha_id = request.query_params.get('cancha', '')
        if cancha_id.isdigit() and not CanchaService.es_visible_para(request.user, cancha_id):
            raise NotFound()
        return super().list(request, *args, **kwargs)

    def guardar(self, serializer):
        self.validar_permisos_por_campo(serializer.validated_data, serializer.instance)
        if serializer.instance is None:
            serializer.instance = HorarioAperturaService.crear(serializer.validated_data)
        else:
            serializer.instance = HorarioAperturaService.actualizar(
                serializer.instance, serializer.validated_data, _confirmado(self.request),
                self.request.user, AuditoriaService.ip_de_request(self.request),
            )

    def perform_destroy(self, instance):
        HorarioAperturaService.dar_de_baja(
            instance, _confirmado(self.request), self.request.user, AuditoriaService.ip_de_request(self.request),
        )


def _validar_filtros_de_complejo(request):
    """Filtrar por un complejo o una cancha ajenos responde 404, igual que pedirlos por id."""
    complejo_id = request.query_params.get('complejo', '')
    if complejo_id.isdigit() and not AccesoComplejoService.puede_administrar(request.user, complejo_id):
        raise NotFound()
    cancha_id = request.query_params.get('cancha', '')
    if cancha_id.isdigit() and not CanchaService.es_visible_para(request.user, cancha_id):
        raise NotFound()


class ExcepcionHorariaViewSet(AccesoComplejoMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                              mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = ExcepcionHorariaSerializer
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'list': ('ver_excepciones',),
        'retrieve': ('ver_excepciones',),
        'create': ('gestionar_excepciones',),
        'destroy': ('gestionar_excepciones',),
    }
    lookup_value_regex = r'\d+'
    queryset = ExcepcionHorariaService.listar()
    filterset_class = ExcepcionHorariaFilter
    ordering_fields = ('fecha_inicio', 'fecha_creacion', 'id')
    ordering = ('fecha_inicio', 'hora_inicio', 'id')
    filter_backends = (DjangoFilterBackend, OrderingFilter)

    def list(self, request, *args, **kwargs):
        _validar_filtros_de_complejo(request)
        return super().list(request, *args, **kwargs)

    def guardar(self, serializer):
        serializer.instance = ExcepcionHorariaService.crear(
            serializer.validated_data, self.request.user, AuditoriaService.ip_de_request(self.request),
        )

    def perform_destroy(self, instance):
        ExcepcionHorariaService.dar_de_baja(
            instance.pk, self.request.user, AuditoriaService.ip_de_request(self.request),
        )


class ReservaViewSet(viewsets.GenericViewSet):
    """Reservas del jugador: solo ve y cancela las propias; las ajenas responden 404."""

    serializer_class = ReservaPropiaSerializer
    permission_classes = [TienePermisoRBAC]
    permisos_requeridos = {
        'create': ('reservar_turno',),
        'mias': ('ver_reservas_propias',),
        'cancelar': ('cancelar_reserva_propia',),
    }
    lookup_value_regex = r'\d+'
    filterset_class = ReservaPropiaFilter
    ordering_fields = ('fecha_turno', 'hora_inicio', 'fecha_creacion')
    ordering = ('fecha_turno', 'hora_inicio', 'id')

    @property
    def filter_backends(self):
        return (DjangoFilterBackend, OrderingFilter) if self.action == 'mias' else ()

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.action == 'create':
            throttles.append(ReservaRateThrottle())
        return throttles

    def get_queryset(self):
        return ReservaService.propias(self.request.user)

    def create(self, request):
        entrada = ReservaAltaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = ReservaService.crear_reserva(
            entrada.validated_data, request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(ReservaPropiaSerializer(reserva).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def mias(self, request):
        pagina = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        return self.get_paginated_response(self.get_serializer(pagina, many=True).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        reserva = ReservaService.cancelar_por_jugador(
            self.get_object().pk, request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(ReservaPropiaSerializer(reserva).data)


class AgendaViewSet(AccesoComplejoMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Reservas de los complejos que el usuario administra, con los datos de contacto de cada cliente."""

    serializer_class = ReservaAgendaSerializer
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'list': ('ver_agenda',),
        'retrieve': ('ver_agenda',),
        'create': ('gestionar_agenda',),
        'partial_update': ('gestionar_agenda',),
        'cancelar': ('cancelar_reserva_complejo',),
        'reabrir': ('gestionar_agenda',),
    }
    campo_complejo = 'cancha__complejo'
    lookup_value_regex = r'\d+'
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    queryset = ReservaService.agenda()
    filterset_class = AgendaFilter
    ordering_fields = ('fecha_turno', 'hora_inicio', 'fecha_creacion', 'id')
    ordering = ('fecha_turno', 'hora_inicio', 'cancha__nombre', 'id')
    filter_backends = (DjangoFilterBackend, OrderingFilter)

    def list(self, request, *args, **kwargs):
        _validar_filtros_de_complejo(request)
        return super().list(request, *args, **kwargs)

    def create(self, request):
        entrada = ReservaManualSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        AccesoComplejoService.validar_operacion(request.user, entrada.validated_data['cancha'].complejo_id)
        reserva = ReservaService.crear_reserva(
            entrada.validated_data, request.user, AuditoriaService.ip_de_request(request), manual=True,
        )
        return Response(ReservaAgendaSerializer(reserva).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        reserva = self.get_object()
        entrada = ReservaAgendaEdicionSerializer(reserva, data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = ReservaService.actualizar_en_agenda(
            reserva.pk, entrada.validated_data, request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(ReservaAgendaSerializer(reserva).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        reserva = ReservaService.cancelar_por_complejo(
            self.get_object().pk, request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(ReservaAgendaSerializer(reserva).data)

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        reserva = self.get_object()
        entrada = ReaperturaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = ReservaService.reabrir(
            reserva, entrada.validated_data['estado'], entrada.validated_data['confirmar'], request.user,
            AuditoriaService.ip_de_request(request),
        )
        return Response(ReservaAgendaSerializer(reserva).data)


class TurnoFijoViewSet(AccesoComplejoMixin, viewsets.ModelViewSet):
    serializer_class = TurnoFijoSerializer
    permission_classes = [TienePermisoRBAC, AdministraComplejo]
    permisos_requeridos = {
        'list': ('ver_agenda',),
        'retrieve': ('ver_agenda',),
        'create': ('gestionar_turnos_fijos',),
        'partial_update': ('gestionar_turnos_fijos',),
        'destroy': ('gestionar_turnos_fijos',),
        'fechas': ('gestionar_agenda',),
    }
    campo_complejo = 'cancha__complejo'
    lookup_value_regex = r'\d+'
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    queryset = TurnoFijoService.listar()
    filterset_class = TurnoFijoFilter
    ordering_fields = ('dia_semana', 'hora_inicio', 'fecha_inicio_vigencia', 'id')
    ordering = ('cancha_id', 'dia_semana', 'hora_inicio', 'id')
    filter_backends = (DjangoFilterBackend, OrderingFilter)

    def list(self, request, *args, **kwargs):
        _validar_filtros_de_complejo(request)
        pagina = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        # Las fechas en espera se calculan para toda la página con dos consultas, no una por turno fijo.
        contexto = {**self.get_serializer_context(), 'fechas_en_espera': TurnoFijoService.fechas_en_espera(pagina)}
        return self.get_paginated_response(TurnoFijoSerializer(pagina, many=True, context=contexto).data)

    def guardar(self, serializer):
        if serializer.instance is None:
            serializer.instance = TurnoFijoService.crear(serializer.validated_data, self.request.user)
        else:
            serializer.instance = TurnoFijoService.actualizar(
                serializer.instance, serializer.validated_data, _confirmado(self.request),
            )

    def perform_destroy(self, instance):
        TurnoFijoService.dar_de_baja(instance)

    @action(detail=True, methods=['post'])
    def fechas(self, request, pk=None):
        turno_fijo = self.get_object()
        entrada = FechaTurnoFijoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva = ReservaService.registrar_fecha_de_turno_fijo(
            turno_fijo, entrada.validated_data['fecha_turno'], request.user, AuditoriaService.ip_de_request(request),
            entrada.validated_data['accion'],
        )
        return Response(ReservaAgendaSerializer(reserva).data, status=status.HTTP_201_CREATED)


class ContratoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ContratoSerializer
    permission_classes = [TienePermisoRBAC]
    permisos_requeridos = {
        'list': ('ver_contratos',),
        'retrieve': ('ver_contratos',),
        'create': ('administrar_contratos',),
        'partial_update': ('administrar_contratos',),
    }
    lookup_value_regex = r'\d+'
    filter_backends = BACKENDS_DE_LISTADO
    filterset_class = ContratoFilter
    search_fields = ('nombre',)
    ordering_fields = ('nombre', 'estado_contrato', 'fecha_creacion')
    ordering = ('nombre', 'id')

    def get_queryset(self):
        return ContratoService.listar()

    def create(self, request):
        entrada = ContratoAltaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        complejo = ContratoService.crear(entrada.validated_data, request.user, AuditoriaService.ip_de_request(request))
        return Response(ContratoSerializer(complejo).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        complejo = self.get_object()
        entrada = ContratoEstadoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        complejo = ContratoService.cambiar_estado(
            complejo.pk, entrada.validated_data['estado_contrato'], request.user,
            AuditoriaService.ip_de_request(request),
        )
        return Response(ContratoSerializer(complejo).data)


class UsuarioViewSet(PermisosPorCampoMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    serializer_class = UsuarioAdminSerializer
    permission_classes = [TienePermisoRBAC]
    permisos_requeridos = {
        'list': ('ver_usuarios',),
        'retrieve': ('ver_usuarios',),
        'partial_update': ('editar_usuarios',),
    }
    permisos_por_campo = {'estado': 'desactivar_usuarios'}
    lookup_value_regex = r'\d+'
    filter_backends = BACKENDS_DE_LISTADO
    filterset_class = UsuarioFilter
    search_fields = ('nombre_completo', 'email')
    ordering_fields = ('id', 'nombre_completo', 'fecha_creacion')
    ordering = ('id',)

    def get_queryset(self):
        return UsuarioAdminService.listar()

    def partial_update(self, request, pk=None):
        usuario = self.get_object()
        entrada = UsuarioAdminEdicionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        self.validar_permisos_por_campo(entrada.validated_data, usuario)
        usuario = UsuarioAdminService.actualizar(
            usuario.pk, entrada.validated_data, request.user, AuditoriaService.ip_de_request(request),
        )
        return Response(UsuarioAdminSerializer(usuario).data)
