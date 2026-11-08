from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    AuditoriaViewSet,
    LoginView,
    LogoutView,
    PerfilView,
    RefreshView,
    RegistroView,
    SaludView,
)

router = SimpleRouter()
router.register('auditoria', AuditoriaViewSet, basename='auditoria')

urlpatterns = [
    path('health/', SaludView.as_view(), name='salud'),
    path('registro/', RegistroView.as_view(), name='registro'),
    path('token/', LoginView.as_view(), name='token'),
    path('token/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('token/logout/', LogoutView.as_view(), name='token_logout'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    *router.urls,
]
