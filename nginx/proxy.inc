proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
# Se reemplaza, no se acumula: lo que el cliente haya mandado en este encabezado no se acepta.
proxy_set_header X-Forwarded-For $remote_addr;
proxy_set_header X-Forwarded-Proto https;
proxy_connect_timeout 5s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
# Las cabeceras de seguridad las fija nginx (cabeceras-seguridad.inc): se descartan las del servicio para no duplicarlas.
proxy_hide_header X-Content-Type-Options;
proxy_hide_header X-Frame-Options;
proxy_hide_header Referrer-Policy;
proxy_hide_header Strict-Transport-Security;
