FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vacias, la aplicacion usa rutas relativas al dominio con que se la abre (https://<dominio>/api/..., /graphql/ y
# wss://<dominio>/ws/...), que nginx reparte entre Django y Node. Ninguna lleva secretos: llegan al navegador.
ARG VITE_API_DJANGO_URL=""
ARG VITE_API_NODE_URL=""
ARG VITE_WS_URL=""
ENV VITE_API_DJANGO_URL=$VITE_API_DJANGO_URL \
    VITE_API_NODE_URL=$VITE_API_NODE_URL \
    VITE_WS_URL=$VITE_WS_URL

RUN npm run build


FROM nginx:1.27-alpine AS runtime

RUN rm -f /etc/nginx/conf.d/default.conf

# La configuracion de nginx vive en ./nginx (contexto adicional "configuracion_nginx" de docker-compose.yml).
COPY --from=configuracion_nginx cloudflare.conf /etc/nginx/conf.d/00-cloudflare.conf
COPY --from=configuracion_nginx nginx.conf /etc/nginx/conf.d/10-talibre.conf
COPY --from=configuracion_nginx *.inc /etc/nginx/snippets/

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443
