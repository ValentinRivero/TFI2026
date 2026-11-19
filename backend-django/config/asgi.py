import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# La app HTTP se inicializa antes de importar módulos que dependan de los modelos.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from core.routing import websocket_urlpatterns  # noqa: E402
from core.ws_auth import JWTAuthMiddleware  # noqa: E402

# El validador de origen corta antes del handshake las páginas ajenas (Cross-Site WebSocket Hijacking);
# JWTAuthMiddleware va al final para que su identificación prevalezca sobre la de sesión.
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(websocket_urlpatterns)))
    ),
})
