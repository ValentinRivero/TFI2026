from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Núcleo TaLibre'

    def ready(self):
        from django.db.backends.signals import connection_created

        from .filters import registrar_sin_acentos_en_sqlite

        connection_created.connect(registrar_sin_acentos_en_sqlite, dispatch_uid='core_sin_acentos_sqlite')
