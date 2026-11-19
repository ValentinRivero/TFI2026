FROM node:24-alpine

ENV NODE_ENV=production

WORKDIR /app

# Las dependencias van antes que el codigo: un cambio de codigo reutiliza esta capa y el despliegue tarda segundos.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --chown=node:node app.js server.js ./
COPY --chown=node:node src ./src

USER node

EXPOSE 3000

CMD ["node", "server.js"]
