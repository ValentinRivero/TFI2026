import { ESTADOS_RESERVA_CANCELABLES } from '../config/catalogos.js';
import { parsearFecha } from './formatos.js';

export const CANCELACION = Object.freeze({
  PERMITIDA: 'permitida',
  FUERA_DE_MARGEN: 'fuera-de-margen',
  NO_APLICA: 'no-aplica',
});

/** Instante local de una fecha `AAAA-MM-DD` y una hora `HH:MM`, o `null` si alguna no es válida. */
export const instanteDelTurno = (fechaTurno, hora) => {
  const fecha = parsearFecha(fechaTurno);
  const partes = /^(\d{1,2}):(\d{2})/.exec(hora ?? '');
  if (!fecha || !partes) return null;
  fecha.setHours(Number(partes[1]), Number(partes[2]), 0, 0);
  return fecha;
};

/**
 * Qué puede hacer el jugador con una reserva, según su estado y el margen de cancelación del complejo:
 * - `PERMITIDA`: está activa y todavía falta más que el margen (`cancelable_hasta`).
 * - `FUERA_DE_MARGEN`: está activa y por jugar, pero el margen ya pasó: solo el complejo puede resolverla.
 * - `NO_APLICA`: ya terminó o no está en un estado cancelable.
 * El servidor valida igual al cancelar: esto solo decide qué se ofrece en pantalla.
 */
export const estadoDeCancelacion = (reserva, ahora = new Date()) => {
  if (!ESTADOS_RESERVA_CANCELABLES.includes(reserva.estado)) return CANCELACION.NO_APLICA;
  const fin = instanteDelTurno(reserva.fecha_turno, reserva.hora_fin);
  if (fin && fin <= ahora) return CANCELACION.NO_APLICA;
  const limite = Date.parse(reserva.cancelable_hasta);
  return limite > ahora.getTime() ? CANCELACION.PERMITIDA : CANCELACION.FUERA_DE_MARGEN;
};

/**
 * Indica si un turno que se está por reservar ya nace fuera del margen de cancelación del complejo: faltan
 * `horasLimite` horas o menos para su inicio. Es el mismo criterio con el que el servidor rechaza cancelar
 * (solo se cancela mientras falte más que el margen), así que se avisa antes de reservar.
 */
export const nacerSinCancelacion = (fechaTurno, horaInicio, horasLimite, ahora = new Date()) => {
  const inicio = instanteDelTurno(fechaTurno, horaInicio);
  if (!inicio || !Number.isFinite(horasLimite) || horasLimite <= 0) return false;
  return inicio.getTime() - horasLimite * 3_600_000 <= ahora.getTime();
};
