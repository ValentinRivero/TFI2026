#!/usr/bin/env python
import os
import sys


def main():
    # Los tests nunca usan la base definida en DATABASE_URL.
    configuracion = 'config.settings_test' if sys.argv[1:2] == ['test'] else 'config.settings'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', configuracion)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'No se pudo importar Django. Verificá que el entorno virtual esté activo '
            'y que las dependencias de requirements.txt estén instaladas.'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
