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
  catalogo: Object.freeze({ busquedaDemoraMs: 400, serviciosEnTarjeta: 4 }),
  // Fuente del pronóstico: su licencia (CC BY 4.0) exige mostrarla junto al clima.
  atribuciones: Object.freeze({
    clima: Object.freeze({ nombre: 'Open-Meteo.com', url: 'https://open-meteo.com/', licencia: 'CC BY 4.0' }),
  }),
  notificaciones: Object.freeze({ sondeoMs: 60_000 }),
  // `paginasMaximas` acota los selectores que necesitan todos los registros de una colección chica (complejos
  // administrados, canchas de un complejo, rangos horarios de una cancha). Los demás valores son espejos de
  // HORAS_CANCELACION_MAXIMAS, LATITUD_MAXIMA y LONGITUD_MAXIMA de Django (core/models.py).
  panel: Object.freeze({
    paginasMaximas: 10,
    horasCancelacionMaximas: 168,
    latitudMaxima: 90,
    longitudMaxima: 180,
  }),
  // Espejo de POLITICA_PRIVACIDAD_VERSION de Django.
  politica: Object.freeze({
    version: '1.0',
    vigenteDesde: '2026-11-12',
    contacto: 'contactotalibre@irracional.net',
    // Espejos de AUDITORIA_RETENCION_MESES y CONTACTOS_BAJA_DIAS de Django.
    retencionIpMeses: 12,
    retencionContactoDias: 30,
  }),
  // Espejo de los largos máximos de los campos de Django (core/models.py).
  limitesCampos: Object.freeze({
    nombre: 120,
    email: 120,
    telefono: 30,
    password: 128,
    busqueda: 100,
    direccion: 160,
    infoSena: 200,
    nombreCancha: 80,
    descripcion: 255,
  }),
  password: Object.freeze({ largoMinimo: 8 }),
  pwa: Object.freeze({ claveBannerCerrado: 'talibre.bannerPwaCerrado' }),
});
