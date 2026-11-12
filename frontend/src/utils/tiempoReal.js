import { PARAMETROS } from '../config/parametros.js';

/**
 * Espera antes del reintento número `intento` (0 para el primero): crece al doble desde `reconexionInicialMs` hasta
 * `reconexionMaximaMs`, y se le suma o resta hasta `jitter` (fracción) al azar para que los clientes que perdieron la conexión
 * a la vez no vuelvan todos al mismo instante. `azar` devuelve un número en [0, 1) y se inyecta para poder probarlo.
 */
export const calcularEspera = (
  intento,
  { reconexionInicialMs, reconexionMaximaMs, jitter } = PARAMETROS.ws,
  azar = Math.random,
) => {
  const base = Math.min(reconexionMaximaMs, reconexionInicialMs * 2 ** Math.max(0, intento));
  const variacion = 1 + jitter * (2 * azar() - 1);
  return Math.round(Math.max(0, base * variacion));
};

/**
 * Dirección del canal de disponibilidad de un complejo. El token se envía solo si hay sesión: sin él (o con uno
 * inválido) el backend atiende la conexión como anónima, en modo lectura.
 */
export const armarUrlDisponibilidad = (base, complejoId, token = null) => {
  const raiz = base.replace(/\/+$/, '');
  const url = `${raiz}/ws/complejos/${encodeURIComponent(complejoId)}/disponibilidad/`;
  return token ? `${url}?token=${encodeURIComponent(token)}` : url;
};

/**
 * Decide si un mensaje del canal obliga a pedir de nuevo la grilla visible. Solo `grilla_actualizada` cuenta.
 * - Fecha: la visible debe caer en el rango del evento (`fecha_hasta` nulo es vigencia sin fin).
 * - Cancha: un evento sin cancha es global; con cancha, debe estar entre las que muestra la grilla.
 * Un evento sin rango de fechas, o sin conocer todavía las canchas, se toma como relevante: recargar de más
 * cuesta una consulta; no recargar deja un casillero desactualizado.
 */
export const eventoAfectaGrilla = (evento, { fecha, canchaIds = null }) => {
  if (evento === null || typeof evento !== 'object' || evento.event !== 'grilla_actualizada') return false;

  const desde = evento.fecha_desde ?? null;
  const hasta = evento.fecha_hasta ?? null;
  if (desde !== null && fecha < desde) return false;
  if (hasta !== null && fecha > hasta) return false;

  if (evento.cancha_id === null || evento.cancha_id === undefined || canchaIds === null) return true;
  return canchaIds.includes(evento.cancha_id);
};
