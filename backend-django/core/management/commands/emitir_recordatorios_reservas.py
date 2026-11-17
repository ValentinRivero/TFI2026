from django.conf import settings
from django.core.management.base import BaseCommand

from core.services import RecordatorioService


class Command(BaseCommand):
    help = (
        'Avisa a cada jugador, en su bandeja de notificaciones, de las reservas activas que empiezan dentro de '
        'RECORDATORIO_HORAS_ANTICIPACION horas. Se puede correr las veces que se quiera: cada reserva se recuerda una '
        'sola vez. Pensado para correr cada hora.'
    )

    def handle(self, *args, **opciones):
        cantidad = RecordatorioService.emitir_pendientes()
        self.stdout.write(
            f'Recordatorios enviados a backend-node: {cantidad} (anticipación: {settings.RECORDATORIO_HORAS_ANTICIPACION} h)'
        )
