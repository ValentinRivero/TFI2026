from django.urls import re_path

from .consumers import DisponibilidadConsumer

websocket_urlpatterns = [
    re_path(r'^ws/complejos/(?P<complejo_id>\d+)/disponibilidad/$', DisponibilidadConsumer.as_asgi()),
]
