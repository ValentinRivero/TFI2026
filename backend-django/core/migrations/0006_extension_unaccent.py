from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Habilita unaccent para las búsquedas sin tildes. En motores que no son PostgreSQL no hace nada."""

    dependencies = [
        ('core', '0005_horarios_con_cortes'),
    ]

    operations = [
        UnaccentExtension(),
    ]
