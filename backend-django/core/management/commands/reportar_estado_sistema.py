from django.core.management.base import BaseCommand

from core.services import EstadoSistemaService


class Command(BaseCommand):
    help = (
        'Mide el estado y la carga del servidor (base de datos, reservas y backend-node) y lo avisa a la bandeja '
        'personal de cada superadministrador. Con --solo-degradado avisa únicamente si algo se degradó, para correrlo '
        'cada pocos minutos; sin esa opción emite el reporte periódico, uno por hora como máximo.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--solo-degradado', action='store_true', help='No avisar si todo está normal.')

    def handle(self, *args, **opciones):
        reporte = EstadoSistemaService.emitir_reporte_estado_servidor(solo_si_degradado=opciones['solo_degradado'])
        if reporte is None:
            self.stdout.write('Estado normal: no se emitió ningún aviso.')
            return
        estado = 'degradado' if reporte['motivos'] else 'normal'
        self.stdout.write(f'Reporte de estado emitido a los superadministradores ({estado}).')
