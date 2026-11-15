/**
 * Parámetros operativos de backend-node en un solo lugar.
 *
 * - `LIMITES`: reglas fijas del servicio. No dependen del entorno: el frontend y la API principal replican varias.
 * - `leerParametros(entorno)`: parámetros ajustables por variable de entorno, con rango y valor por defecto. Un valor
 *   inválido lanza un error con el nombre de la variable, en lugar de caer en silencio al valor por defecto.
 * - `obtenerParametros()`: lectura del entorno real, en el momento de uso. Importar este módulo no lee el entorno.
 *
 * Los secretos y direcciones (`JWT_SIGNING_KEY`, `INTERNAL_API_KEY`, `DJANGO_API_URL`, `MONGO_URI` y
 * `CORS_ALLOWED_ORIGINS`) no pasan por acá: cada módulo los lee al usarlos.
 */

export const LIMITES = Object.freeze({
  paginacion: Object.freeze({ tamanoDePagina: 20, maximoPorPagina: 50 }),
  diasDePronostico: 3,
  maximoMensaje: 280,
  maximoBytesMetadata: 2048,
  largoMinimoClaveInterna: 32,
});

const URL_CLIMA_POR_DEFECTO = 'https://api.open-meteo.com/v1/forecast';

const entero = (entorno, nombre, porDefecto, { minimo, maximo }) => {
  const crudo = entorno[nombre];
  if (crudo === undefined || String(crudo).trim() === '') return porDefecto;
  const texto = String(crudo).trim();
  if (!/^-?\d+$/.test(texto)) throw new Error(`${nombre} debe ser un número entero.`);
  const numero = Number(texto);
  if (numero < minimo || numero > maximo) throw new Error(`${nombre} debe ser un entero entre ${minimo} y ${maximo}.`);
  return numero;
};

const direccionHttp = (entorno, nombre, porDefecto) => {
  const crudo = entorno[nombre];
  if (crudo === undefined || String(crudo).trim() === '') return porDefecto;
  const texto = String(crudo).trim();
  let direccion;
  try {
    direccion = new URL(texto);
  } catch {
    throw new Error(`${nombre} debe ser una URL http o https.`);
  }
  if (!['http:', 'https:'].includes(direccion.protocol) || direccion.username || direccion.password) {
    throw new Error(`${nombre} debe ser una URL http o https sin credenciales.`);
  }
  return texto;
};

const limitador = (entorno, prefijo, ventanaPorDefecto, maximoPorDefecto) => Object.freeze({
  ventanaMs: entero(entorno, `${prefijo}_VENTANA_MS`, ventanaPorDefecto, { minimo: 1_000, maximo: 86_400_000 }),
  maximo: entero(entorno, `${prefijo}_MAXIMO`, maximoPorDefecto, { minimo: 1, maximo: 1_000_000 }),
});

export const leerParametros = (entorno) => Object.freeze({
  puerto: entero(entorno, 'PORT', 3000, { minimo: 1, maximo: 65_535 }),
  // Saltos de proxy de confianza (nginx): sin esto el limitador vería a todos los clientes con la IP del proxy.
  numProxies: entero(entorno, 'NUM_PROXIES', 0, { minimo: 0, maximo: 10 }),
  limitadores: Object.freeze({
    global: limitador(entorno, 'RATE_LIMIT', 60_000, 120),
    actividad: limitador(entorno, 'RATE_LIMIT_ACTIVIDAD', 60_000, 30),
    interno: limitador(entorno, 'RATE_LIMIT_INTERNO', 60_000, 600),
  }),
  clima: Object.freeze({
    url: direccionHttp(entorno, 'CLIMA_URL', URL_CLIMA_POR_DEFECTO),
    // Open-Meteo actualiza el clima actual cada 15 minutos: antes no hay datos nuevos que pedir.
    ttlMs: entero(entorno, 'CLIMA_TTL_MS', 15 * 60 * 1000, { minimo: 1_000, maximo: 86_400_000 }),
    cacheMaximo: entero(entorno, 'CLIMA_CACHE_MAXIMO', 500, { minimo: 1, maximo: 100_000 }),
  }),
  http: Object.freeze({
    timeoutDjangoMs: entero(entorno, 'HTTP_TIMEOUT_DJANGO_MS', 5_000, { minimo: 100, maximo: 60_000 }),
    timeoutClimaMs: entero(entorno, 'HTTP_TIMEOUT_CLIMA_MS', 5_000, { minimo: 100, maximo: 60_000 }),
  }),
  // Los eventos y notificaciones son livianos: un cuerpo mayor es un error del cliente o un intento de abuso.
  bodyMaximoBytes: entero(entorno, 'BODY_MAXIMO_BYTES', 10 * 1024, { minimo: 1_024, maximo: 1_048_576 }),
  mongo: Object.freeze({
    timeoutSeleccionMs: entero(entorno, 'MONGO_TIMEOUT_SELECCION_MS', 10_000, { minimo: 1_000, maximo: 60_000 }),
    maxPoolSize: entero(entorno, 'MONGO_MAX_POOL', 100, { minimo: 1, maximo: 500 }),
  }),
  // Mismo tope que el dashboard de la API principal (RANGO_MAXIMO_DIAS), que muestra estas métricas junto a las suyas.
  rangoMaximoDias: entero(entorno, 'RANGO_MAXIMO_DIAS', 366, { minimo: 1, maximo: 3_660 }),
});

export const obtenerParametros = () => leerParametros(process.env);
