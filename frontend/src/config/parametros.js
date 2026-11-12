/**
 * Parámetros operativos del cliente en un solo lugar. Ninguna página ni componente lleva números, URLs ni claves
 * de almacenamiento sueltos. Varios valores replican reglas de los backends (ver PROJECT.md §14.2): se cambian en
 * ambos lados en la misma tarea.
 */
const entorno = import.meta.env;

// Solo los servicios (`api.js`, `wsService.js`) importan las URLs: las páginas nunca conocen una dirección de API.
export const ENTORNO = Object.freeze({
  urlDjango: entorno.VITE_API_DJANGO_URL ?? 'http://localhost:8000',
  urlNode: entorno.VITE_API_NODE_URL ?? 'http://localhost:3000',
  urlWs: entorno.VITE_WS_URL ?? 'ws://localhost:8000',
  desarrollo: entorno.DEV,
});

export const PARAMETROS = Object.freeze({
  idioma: 'es',
  formato: Object.freeze({ locale: 'es-AR', moneda: 'ARS' }),
  // Espejo de PAGE_SIZE de Django y del límite por defecto de Node.
  paginacion: Object.freeze({ tamanio: 20, botones: 5 }),
  http: Object.freeze({ timeoutDjangoMs: 15_000, timeoutNodeMs: 15_000 }),
  ws: Object.freeze({
    reconexionInicialMs: 1_000,
    reconexionMaximaMs: 30_000,
    jitter: 0.3,
    agruparEventosMs: 1_000,
  }),
  mapa: Object.freeze({
    centro: [-29.14, -59.26],
    zoom: 13,
    zoomMinimo: 11,
    zoomMaximo: 18,
    teselas: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    atribucion: '© OpenStreetMap contributors',
  }),
  notificaciones: Object.freeze({ sondeoMs: 60_000 }),
  // Espejo de POLITICA_PRIVACIDAD_VERSION de Django.
  politica: Object.freeze({ version: '1.0', contacto: 'contactotalibre@irracional.net' }),
  pwa: Object.freeze({ claveBannerCerrado: 'talibre.bannerPwaCerrado' }),
});
