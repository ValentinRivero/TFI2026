from django.conf import settings
from django.core.management.base import BaseCommand

from core.services import AuditoriaService


class Command(BaseCommand):
    help = (
        'Anonimiza la IP de origen de los registros de auditoría con más de AUDITORIA_RETENCION_MESES meses. '
        'Conserva el evento, la fecha y el usuario. Pensado para correr una vez por mes.'
    )

    def handle(self, *args, **opciones):
        cantidad = AuditoriaService.anonimizar_ips_vencidas()
        self.stdout.write(
            f'Registros de auditoría con la IP anonimizada: {cantidad} (retención: {settings.AUDITORIA_RETENCION_MESES} meses)'
        )
