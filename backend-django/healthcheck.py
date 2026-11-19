"""Healthcheck del contenedor: consulta la ruta de salud de Daphne con un Host que Django acepta."""
import os
import sys
import urllib.request

host = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost').split(',')[0].strip().lstrip('.') or 'localhost'
pedido = urllib.request.Request('http://127.0.0.1:8000/api/health/', headers={'Host': host})

try:
    with urllib.request.urlopen(pedido, timeout=4) as respuesta:
        sys.exit(0 if respuesta.status == 200 else 1)
except Exception:
    sys.exit(1)
