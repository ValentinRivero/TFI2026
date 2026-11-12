from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from core.graphql_views import JWTGraphQLView

from .schema import schema

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    # Sin CSRF: la autenticación viaja en el encabezado Authorization, nunca en una cookie de sesión.
    path('graphql/', csrf_exempt(JWTGraphQLView.as_view(schema=schema, graphiql=True))),
]
