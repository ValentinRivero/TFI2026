from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AgendaViewSet,
    AuditoriaViewSet,
    CanchaViewSet,
    ComplejoViewSet,
    ContratoViewSet,
    DeporteViewSet,
    ExcepcionHorariaViewSet,
    HorarioAperturaViewSet,
    LoginView,
    LogoutView,
    PerfilBajaView,
    PerfilView,
    RefreshView,
    RegistroView,
    ReservaViewSet,
    SaludView,
    ServicioViewSet,
    TurnoFijoViewSet,
    UsuarioViewSet,
)

router = SimpleRouter()
router.register('auditoria', AuditoriaViewSet, basename='auditoria')
router.register('deportes', DeporteViewSet, basename='deporte')
router.register('servicios', ServicioViewSet, basename='servicio')
router.register('complejos', ComplejoViewSet, basename='complejo')
router.register('canchas', CanchaViewSet, basename='cancha')
router.register('horarios', HorarioAperturaViewSet, basename='horario')
router.register('excepciones', ExcepcionHorariaViewSet, basename='excepcion')
router.register('reservas', ReservaViewSet, basename='reserva')
router.register('agenda', AgendaViewSet, basename='agenda')
router.register('turnos-fijos', TurnoFijoViewSet, basename='turno-fijo')
router.register('contratos', ContratoViewSet, basename='contrato')
router.register('usuarios', UsuarioViewSet, basename='usuario')

urlpatterns = [
    path('health/', SaludView.as_view(), name='salud'),
    path('registro/', RegistroView.as_view(), name='registro'),
    path('token/', LoginView.as_view(), name='token'),
    path('token/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('token/logout/', LogoutView.as_view(), name='token_logout'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/baja/', PerfilBajaView.as_view(), name='perfil_baja'),
    *router.urls,
]
