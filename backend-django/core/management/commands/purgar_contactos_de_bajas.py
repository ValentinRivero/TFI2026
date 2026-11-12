from django.conf import settings
from django.core.management.base import BaseCommand

from core.services import BajaDeCuentaService


class Command(BaseCommand):
    help = (
        'Borra el nombre y el teléfono conservados de titulares dados de baja en reservas cuyo turno superó el plazo '
        'de CONTACTOS_BAJA_DIAS. Pensado para correr una vez por día.'
    )

    def handle(self, *args, **opciones):
        cantidad = BajaDeCuentaService.purgar_contactos_vencidos()
        self.stdout.write(
            f'Reservas con datos de contacto depurados: {cantidad} (plazo: {settings.CONTACTOS_BAJA_DIAS} días)'
        )
