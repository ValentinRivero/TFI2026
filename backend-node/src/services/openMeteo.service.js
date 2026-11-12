import { LIMITES, obtenerParametros } from '../config/parametros.js';
import { ErrorServicioExterno } from '../middlewares/errores.middleware.js';

const DIAS_DE_PRONOSTICO = LIMITES.diasDePronostico;
// Las fechas del pronóstico salen en hora de Argentina, igual que la grilla y los reportes.
const ZONA_HORARIA = 'America/Argentina/Buenos_Aires';

const VARIABLES_ACTUALES = ['temperature_2m', 'weather_code', 'wind_speed_10m', 'precipitation', 'is_day'];
const VARIABLES_DIARIAS = [
  'weather_code', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_probability_max',
];
// El modelo puede no tener probabilidad de lluvia para algún día: se informa como `null`.
const DIARIAS_OPCIONALES = new Set(['precipitation_probability_max']);

// Códigos WMO que usa Open-Meteo en `weather_code`.
const DESCRIPCIONES = new Map([
  [[0], 'Despejado'],
  [[1], 'Mayormente despejado'],
  [[2], 'Parcialmente nublado'],
  [[3], 'Nublado'],
  [[45, 48], 'Niebla'],
  [[51, 53, 55], 'Llovizna'],
  [[56, 57], 'Llovizna helada'],
  [[61], 'Lluvia leve'],
  [[63], 'Lluvia moderada'],
  [[65], 'Lluvia intensa'],
  [[66, 67], 'Lluvia helada'],
  [[71, 73, 75], 'Nevada'],
  [[77], 'Granos de nieve'],
  [[80], 'Chaparrones leves'],
  [[81], 'Chaparrones moderados'],
  [[82], 'Chaparrones fuertes'],
  [[85, 86], 'Chaparrones de nieve'],
  [[95], 'Tormenta'],
  [[96, 99], 'Tormenta con granizo'],
].flatMap(([codigos, texto]) => codigos.map((codigo) => [codigo, texto])));

export const describirCodigo = (codigo) => DESCRIPCIONES.get(codigo) ?? 'Sin descripción';

const falla = (causa) => {
  console.error('Open-Meteo no respondió como se esperaba:', causa.message);
  return new ErrorServicioExterno('Open-Meteo', causa);
};

const esNumero = (valor) => typeof valor === 'number' && Number.isFinite(valor);

// Se controla la forma antes de usarla: una respuesta inesperada es una falla del proveedor (502), no un 500.
const esPronosticoValido = (datos) => {
  if (datos === null || typeof datos !== 'object') return false;
  const { current: actual, daily: diario } = datos;
  if (!actual || typeof actual.time !== 'string' || !VARIABLES_ACTUALES.every((v) => esNumero(actual[v]))) {
    return false;
  }
  if (!diario || !Array.isArray(diario.time) || diario.time.length === 0) return false;
  return VARIABLES_DIARIAS.every((variable) => Array.isArray(diario[variable])
    && diario[variable].length === diario.time.length
    && diario[variable].every((valor) => esNumero(valor) || (valor === null && DIARIAS_OPCIONALES.has(variable))));
};

const aRespuestaLiviana = ({ current: actual, daily: diario }) => ({
  actual: {
    fecha_hora: actual.time,
    temperatura: actual.temperature_2m,
    codigo_clima: actual.weather_code,
    descripcion: describirCodigo(actual.weather_code),
    viento_kmh: actual.wind_speed_10m,
    precipitacion_mm: actual.precipitation,
    es_de_dia: actual.is_day === 1,
  },
  pronostico: diario.time.map((fecha, i) => ({
    fecha,
    codigo_clima: diario.weather_code[i],
    descripcion: describirCodigo(diario.weather_code[i]),
    temperatura_max: diario.temperature_2m_max[i],
    temperatura_min: diario.temperature_2m_min[i],
    probabilidad_lluvia: diario.precipitation_probability_max[i],
  })),
});

/** Clima actual y de los próximos días en unas coordenadas, con solo los campos que muestra el frontend. */
export const obtenerPronostico = async ({ latitud, longitud }) => {
  const parametros = new URLSearchParams({
    latitude: latitud,
    longitude: longitud,
    current: VARIABLES_ACTUALES.join(','),
    daily: VARIABLES_DIARIAS.join(','),
    timezone: ZONA_HORARIA,
    forecast_days: DIAS_DE_PRONOSTICO,
  });

  const { clima, http } = obtenerParametros();
  let respuesta;
  try {
    respuesta = await fetch(`${clima.url}?${parametros}`, {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(http.timeoutClimaMs),
      redirect: 'error',
    });
  } catch (error) {
    throw falla(error);
  }
  if (!respuesta.ok) throw falla(new Error(`HTTP ${respuesta.status} en el pronóstico`));

  let datos;
  try {
    datos = await respuesta.json();
  } catch (error) {
    throw falla(error);
  }
  if (!esPronosticoValido(datos)) throw falla(new Error('El pronóstico no tiene la forma esperada'));
  return aRespuestaLiviana(datos);
};
