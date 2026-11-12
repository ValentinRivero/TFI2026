import { PARAMETROS } from '../config/parametros.js';

const { locale, moneda } = PARAMETROS.formato;

const FECHA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * `AAAA-MM-DD` como fecha local al mediodía. `new Date('2026-11-18')` la interpreta en UTC y en Argentina muestra
 * el día anterior: por eso se arma por partes. Devuelve `null` si no es una fecha de calendario válida.
 */
export const parsearFecha = (texto) => {
  const partes = FECHA_ISO.exec(texto ?? '');
  if (!partes) return null;
  const [anio, mes, dia] = partes.slice(1).map(Number);
  const fecha = new Date(anio, mes - 1, dia, 12);
  const valida = fecha.getFullYear() === anio && fecha.getMonth() === mes - 1 && fecha.getDate() === dia;
  return valida ? fecha : null;
};

const dosDigitos = (numero) => String(numero).padStart(2, '0');

/** Fecha local como `AAAA-MM-DD`, para armar parámetros de consulta. */
export const aFechaIso = (fecha) => (
  `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}-${dosDigitos(fecha.getDate())}`
);

/** `AAAA-MM-DD` desplazada una cantidad de días (negativa hacia atrás), por partes y sin pasar por UTC. */
export const sumarDias = (texto, dias) => {
  const fecha = parsearFecha(texto);
  if (!fecha) return null;
  fecha.setDate(fecha.getDate() + dias);
  return aFechaIso(fecha);
};

/** Temperatura en grados, redondeada: `18.6` como `"19°"`. */
export const formatearTemperatura = (valor) => (
  typeof valor === 'number' && Number.isFinite(valor) ? `${Math.round(valor)}°` : ''
);

const formateadorEntero = new Intl.NumberFormat(locale, {
  style: 'currency', currency: moneda, minimumFractionDigits: 0, maximumFractionDigits: 0,
});
const formateadorConCentavos = new Intl.NumberFormat(locale, { style: 'currency', currency: moneda });

/** Importe (número o texto decimal como `"38000.00"`) en pesos argentinos; los centavos solo si los hay. */
export const formatearPrecio = (valor) => {
  if (valor === null || valor === undefined || valor === '') return '';
  const numero = Number(valor);
  if (Number.isNaN(numero)) return '';
  return (Number.isInteger(numero) ? formateadorEntero : formateadorConCentavos).format(numero);
};

/** `"14:00:00"` o `"14:00"` como `"14:00"`. */
export const formatearHora = (texto) => {
  const partes = /^(\d{1,2}):(\d{2})/.exec(texto ?? '');
  return partes ? `${dosDigitos(partes[1])}:${partes[2]}` : '';
};

/** Solo la primera letra en mayúscula: "jueves, 12 de noviembre" pasa a "Jueves, 12 de noviembre", sin tocar "de". */
const primeraMayuscula = (texto) => (texto ? texto.charAt(0).toLocaleUpperCase(locale) + texto.slice(1) : texto);

const formateadorFechaLarga = new Intl.DateTimeFormat(locale, { weekday: 'long', day: 'numeric', month: 'long' });
const formateadorFechaCorta = new Intl.DateTimeFormat(locale, { day: '2-digit', month: '2-digit', year: 'numeric' });

/** `AAAA-MM-DD` como "Miércoles, 18 de noviembre". */
export const formatearFechaLarga = (texto) => {
  const fecha = parsearFecha(texto);
  return fecha ? primeraMayuscula(formateadorFechaLarga.format(fecha)) : '';
};

const formateadorMomento = new Intl.DateTimeFormat(locale, {
  weekday: 'short', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit', hour12: false,
});

/** Instante con zona horaria (`2026-11-24T16:00:00-03:00`) como "mar 24 de noviembre, 16:00", en hora local. */
export const formatearMomento = (texto) => {
  if (typeof texto !== 'string' || texto === '') return '';
  const instante = new Date(texto);
  return Number.isNaN(instante.getTime()) ? '' : formateadorMomento.format(instante);
};

const formateadorDiaCorto = new Intl.DateTimeFormat(locale, { weekday: 'short', day: 'numeric' });

/** `AAAA-MM-DD` como "Mié 18". */
export const formatearDiaCorto = (texto) => {
  const fecha = parsearFecha(texto);
  return fecha ? primeraMayuscula(formateadorDiaCorto.format(fecha)) : '';
};

/** `AAAA-MM-DD` como "18/11/2026". */
export const formatearFechaCorta = (texto) => {
  const fecha = parsearFecha(texto);
  return fecha ? formateadorFechaCorta.format(fecha) : '';
};
