FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser \
    && mkdir -p /var/log/talibre \
    && chown appuser:appuser /app /var/log/talibre

# Las dependencias van antes que el codigo: un cambio de codigo reutiliza esta capa y el despliegue tarda segundos.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

# Claves descartables y solo para este paso: collectstatic importa la configuracion, que exige ambas variables.
# Nada de esto queda en la imagen ni se parece a un secreto real.
RUN DJANGO_SECRET_KEY=solo-para-collectstatic-durante-el-build \
    JWT_SIGNING_KEY=solo-para-collectstatic-durante-el-build \
    SECURITY_LOG_PATH=/tmp/build-security.log \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Keepalive explicito del WebSocket: un ping de protocolo cada 20 s de silencio mantiene vivo el canal frente al limite de
# inactividad de Cloudflare (alrededor de 100 s) y limpia conexiones muertas a los 30 s sin respuesta. No depende del
# valor por defecto de la version instalada.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--ping-interval", "20", "--ping-timeout", "30", "config.asgi:application"]
