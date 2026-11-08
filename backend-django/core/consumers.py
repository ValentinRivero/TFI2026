from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .services import DifusionGrillaService, grupo_de_complejo

# Cierre propio (rango 4000-4999 reservado a aplicaciones): el complejo no existe o no publica su grilla.
CIERRE_COMPLEJO_NO_DISPONIBLE = 4404


class DisponibilidadConsumer(AsyncJsonWebsocketConsumer):
    """
    Canal público de solo lectura de la grilla de un complejo. Anónimos y usuarios identificados reciben los
    mismos eventos, que solo llevan ids, fechas y horarios; lo que envíe el cliente se descarta.
    """

    grupo = None

    async def connect(self):
        complejo_id = int(self.scope['url_route']['kwargs']['complejo_id'])
        publica = await database_sync_to_async(DifusionGrillaService.admite_suscripcion)(complejo_id)
        if not publica:
            await self.close(code=CIERRE_COMPLEJO_NO_DISPONIBLE)
            return
        self.grupo = grupo_de_complejo(complejo_id)
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.grupo is not None:
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        # Ni siquiera se decodifica: un mensaje mal formado no puede tirar la conexión de lectura.
        return None

    async def grilla_actualizada(self, mensaje):
        await self.send_json(mensaje['evento'])
