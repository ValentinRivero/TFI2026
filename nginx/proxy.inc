proxy_http_version 1.1;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
# Se reemplaza, no se acumula: lo que el cliente haya mandado en este encabezado no se acepta.
proxy_set_header X-Forwarded-For $remote_addr;
proxy_set_header X-Forwarded-Proto https;
# Los tiempos de envio y lectura quedan en el valor por defecto de nginx (60 s); /ws/ define los suyos.
proxy_connect_timeout 5s;
# Las cabeceras de seguridad las fija nginx (cabeceras-seguridad.inc): se descartan las del servicio para no duplicarlas.
proxy_hide_header X-Content-Type-Options;
proxy_hide_header X-Frame-Options;
proxy_hide_header Referrer-Policy;
proxy_hide_header Strict-Transport-Security;
