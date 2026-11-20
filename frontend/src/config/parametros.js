/**
 * Parámetros operativos del cliente en un solo lugar. Ninguna página ni componente lleva números, URLs ni claves
 * de almacenamiento sueltos. Varios valores replican reglas de los backends (ver PROJECT.md §14.2): se cambian en
 * ambos lados en la misma tarea.
 */
const entorno = import.meta.env;

/**
 * Dirección del WebSocket. Sin definir, apunta al backend local de desarrollo; definida pero vacía (el despliegue
 * detrás de nginx), usa el mismo origen de la página con `wss://` si se abrió por HTTPS: un `new WebSocket('/ws/...')`
 * relativo no lo aceptan todos los navegadores.
 */
export const resolverUrlWs = (valor, ubicacion = globalThis.location) => {
  if (valor === undefined) return 'ws://localhost:8000';
  if (valor !== '') return valor;
  if (!ubicacion) return '';
  return `${ubicacion.protocol === 'https:' ? 'wss:' : 'ws:'}//${ubicacion.host}`;
};

// Solo los servicios (`api.js`, `wsService.js`) importan las URLs: las páginas nunca conocen una dirección de API.
// En el despliegue las tres variables van vacías y todo se pide al mismo dominio (rutas relativas `/api/...`).
export const ENTORNO = Object.freeze({
  urlDjango: entorno.VITE_API_DJANGO_URL ?? 'http://localhost:8000',
  urlNode: entorno.VITE_API_NODE_URL ?? 'http://localhost:3000',
  urlWs: resolverUrlWs(entorno.VITE_WS_URL),
  desarrollo: entorno.DEV,
  produccion: entorno.PROD,
});

export const PARAMETROS = Object.freeze({
  idioma: 'es',
  // Versión de la aplicación que muestra el pie de página: `0.<fase>.<ítem>` del plan (6.4 -> 0.6.4) hasta el despliegue,
  // cuando pasa a 1.0.0 (CLAUDE.md §8.8).
  app: Object.freeze({ version: '0.7.2' }),
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
  // El servicio opera solo en Goya: `limites` ([sudoeste, noreste]) y `zoomMinimo` impiden alejarse del área urbana y
  // periurbana. `zoomEtiquetasVisibles` es el nivel desde el cual el nombre de cada complejo queda siempre visible.
  mapa: Object.freeze({
    centro: [-29.14, -59.26],
    zoom: 13,
    zoomMinimo: 13,
    zoomMaximo: 19,
    limites: Object.freeze([Object.freeze([-29.22, -59.34]), Object.freeze([-29.07, -59.18])]),
    viscosidadLimites: 0.9,
    zoomEtiquetasVisibles: 15,
    // Con un solo complejo (o muy juntos) el ajuste de la vista no se acerca más que este nivel.
    zoomAjusteMaximo: 16,
    margenAjustePx: 40,
    anchoPopupPx: 232,
    // Teselas de calles, pedidas sin clave, con las atribuciones que exigen sus proveedores. `zoomNativoMaximo` es el
    // último nivel con datos reales en Goya: más cerca se amplía ese nivel.
    teselas: Object.freeze({
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      zoomNativoMaximo: 19,
    }),
    atribuciones: Object.freeze([
      Object.freeze({ texto: 'Tiles © Esri', url: 'https://www.esri.com/', licencia: 'Esri World Street Map' }),
      Object.freeze({ texto: '© OpenStreetMap contributors', url: 'https://www.openstreetmap.org/copyright', licencia: 'ODbL' }),
    ]),
  }),
  catalogo: Object.freeze({ busquedaDemoraMs: 400, serviciosEnTarjeta: 4 }),
  // Fuente del pronóstico: su licencia (CC BY 4.0) exige mostrarla junto al clima.
  atribuciones: Object.freeze({
    clima: Object.freeze({ nombre: 'Open-Meteo.com', url: 'https://open-meteo.com/', licencia: 'CC BY 4.0' }),
  }),
  // `contadorMaximo`: desde esa cantidad la campana muestra "99+" en lugar del número exacto.
  notificaciones: Object.freeze({ sondeoMs: 60_000, contadorMaximo: 99 }),
  // Redes del pie de página. Los usuarios son de muestra (no corresponden a cuentas reales) y los enlaces llevan a la
  // portada de cada red; al contar con las cuentas oficiales se reemplazan `usuario` y `url`. Solo se muestran las que
  // tienen una `url` https.
  pie: Object.freeze({
    redes: Object.freeze([
      Object.freeze({ clave: 'instagram', icono: 'instagram', usuario: '@talibre.goya', url: 'https://www.instagram.com/' }),
      Object.freeze({ clave: 'facebook', icono: 'facebook', usuario: '@talibre.goya', url: 'https://www.facebook.com/' }),
      Object.freeze({ clave: 'twitter', icono: 'twitter', usuario: '@talibre_goya', url: 'https://x.com/' }),
    ]),
  }),
  // `paginasMaximas` acota los selectores que necesitan todos los registros de una colección chica (complejos
  // administrados, canchas de un complejo, rangos horarios de una cancha). Los demás valores son espejos de
  // HORAS_CANCELACION_DEFECTO, HORAS_CANCELACION_MAXIMAS, LATITUD_MAXIMA y LONGITUD_MAXIMA de Django (core/models.py).
  panel: Object.freeze({
    paginasMaximas: 10,
    horasCancelacionDefecto: 4,
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
  // `proximasFechas`: cuántas fechas futuras de un turno fijo se ofrecen al llevarlas a la agenda.
  agenda: Object.freeze({ proximasFechas: 8 }),
  // Espejo de RANGO_MAXIMO_DIAS de Django y de Node (rango máximo de un reporte, en días, ambos extremos incluidos).
  reportes: Object.freeze({ rangoMaximoDias: 366 }),
  password: Object.freeze({ largoMinimo: 8 }),
  // Espejo de LARGO_MINIMO_NOMBRE, LARGO_MINIMO_EMAIL y SIMBOLOS_PASSWORD de Django (core/models.py): reglas de los campos
  // de cuenta. El largo mínimo de la contraseña es `password.largoMinimo` y los máximos están en `limitesCampos`.
  cuenta: Object.freeze({ nombreLargoMinimo: 2, emailLargoMinimo: 6, passwordSimbolos: '!@#$%^&*()_+-=.,:;?/' }),
  // Espejo de `diasDePronostico` de backend-node: la franja compacta del clima reserva el alto de esa cantidad de días.
  clima: Object.freeze({ diasDePronostico: 3 }),
  pwa: Object.freeze({ claveBannerCerrado: 'talibre.bannerPwaCerrado', rutaServiceWorker: '/sw.js' }),
  // Espejo del script de arranque de index.html (que aplica el tema antes de montar React) y de `--tema-pizarra` en
  // tema.css: la clave del almacenamiento, la consulta de preferencia del sistema y el color de la barra del navegador
  // coinciden con los de ese script. `utils/tema.test.js` verifica que sigan siendo iguales.
  tema: Object.freeze({
    claveAlmacenamiento: 'talibre_tema',
    consultaOscuro: '(prefers-color-scheme: dark)',
    colorBarra: Object.freeze({ light: '#0f172a', dark: '#0b1322' }),
  }),
});
