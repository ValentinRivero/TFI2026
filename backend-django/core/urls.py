from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AuditoriaViewSet,
    CanchaViewSet,
    ComplejoViewSet,
    ContratoViewSet,
    DeporteViewSet,
    ExcepcionHorariaViewSet,
    HorarioAperturaViewSet,
    LoginView,
    LogoutView,
    PerfilView,
    RefreshView,
    RegistroView,
    SaludView,
    ServicioViewSet,
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
router.register('contratos', ContratoViewSet, basename='contrato')
router.register('usuarios', UsuarioViewSet, basename='usuario')

urlpatterns = [
    path('health/', SaludView.as_view(), name='salud'),
    path('registro/', RegistroView.as_view(), name='registro'),
    path('token/', LoginView.as_view(), name='token'),
    path('token/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('token/logout/', LogoutView.as_view(), name='token_logout'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    *router.urls,
]
