from django.core.management.base import BaseCommand

from core.services import DIAS_DE_CONSERVACION_DE_CONTACTO, BajaDeCuentaService


class Command(BaseCommand):
    help = (
        'Borra el nombre y el teléfono conservados de titulares dados de baja en reservas cuyo turno fue hace más de '
        f'{DIAS_DE_CONSERVACION_DE_CONTACTO} días. Pensado para correr una vez por día.'
    )

    def handle(self, *args, **opciones):
        cantidad = BajaDeCuentaService.purgar_contactos_vencidos()
        self.stdout.write(f'Reservas con datos de contacto depurados: {cantidad}')
