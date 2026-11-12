import {
  ESTADOS_QUE_EXIGEN_TURNO_INICIADO,
  ESTADOS_RESERVA_CANCELABLES,
  ESTADOS_RESERVA_CANCELADOS,
  TRANSICIONES_AGENDA,
  VISTA_AGENDA,
} from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { parsearFecha } from './formatos.js';
import { instanteDelTurno } from './reservas.js';

/** Vista de la agenda que pide la ruta (`?vista=`); un valor desconocido o ausente abre las reservas del día. */
export const vistaDeAgenda = (valor) => (
  Object.values(VISTA_AGENDA).includes(valor) ? valor : VISTA_AGENDA.RESERVAS
);

/** La agenda abre en el día de hoy; sin fecha lista todas las reservas del complejo. */
export const filtrosAgendaIniciales = (hoy) => ({ fecha: hoy, cancha: '', estado: '', conConflicto: false });

/**
 * Parámetros de `GET /api/agenda/` para el complejo, los filtros y la página. Un filtro vacío o una fecha que no es
 * de calendario no viaja: el backend responde 400 ante un valor inválido.
 */
export const aParametrosAgenda = (complejoId, filtros, pagina) => {
  const params = { complejo: complejoId, page: pagina };
  if (parsearFecha(filtros.fecha)) params.fecha = filtros.fecha;
  if (filtros.cancha) params.cancha = filtros.cancha;
  if (filtros.estado) params.estado = filtros.estado;
  if (filtros.conConflicto) params.con_conflicto = true;
  return params;
};

const yaComenzo = (reserva, ahora) => {
  const inicio = instanteDelTurno(reserva.fecha_turno, reserva.hora_inicio);
  return Boolean(inicio) && inicio <= ahora;
};

/**
 * Estados a los que se puede pasar una reserva desde la agenda: las transiciones del backend, sin ausente ni
 * completada mientras el turno no empezó. El servidor valida igual: esto solo decide qué se ofrece.
 */
export const estadosSiguientes = (reserva, ahora = new Date()) => (
  (TRANSICIONES_AGENDA[reserva.estado] ?? []).filter(
    (estado) => !ESTADOS_QUE_EXIGEN_TURNO_INICIADO.includes(estado) || yaComenzo(reserva, ahora),
  )
);

/** Una reserva pendiente, confirmada o señada la puede cancelar el complejo sin restricción horaria. */
export const puedeCancelarElComplejo = (reserva) => ESTADOS_RESERVA_CANCELABLES.includes(reserva.estado);

/** Se reabre una reserva cancelada cuyo turno todavía no empezó. */
export const puedeReabrir = (reserva, ahora = new Date()) => (
  ESTADOS_RESERVA_CANCELADOS.includes(reserva.estado) && !yaComenzo(reserva, ahora)
);

export const VALORES_RESERVA_MANUAL_INICIALES = Object.freeze({
  cancha: '',
  fecha_turno: '',
  hora_inicio: '',
  nombre_cliente_manual: '',
  telefono_cliente_manual: '',
  observaciones: '',
});

/** Errores por campo del alta manual; `hoy` es `AAAA-MM-DD`. Un objeto vacío significa que se puede enviar. */
export const validarReservaManual = (valores, hoy) => {
  const errores = {};
  if (!valores.cancha) errores.cancha = t('agenda.errorCancha');
  if (!parsearFecha(valores.fecha_turno)) errores.fecha_turno = t('agenda.errorFecha');
  else if (valores.fecha_turno < hoy) errores.fecha_turno = t('agenda.errorPasado');
  if (!valores.hora_inicio) errores.hora_inicio = t('agenda.errorHora');
  if (valores.nombre_cliente_manual.trim() === '') errores.nombre_cliente_manual = t('agenda.errorNombre');
  return errores;
};

/** Cuerpo del `POST /api/agenda/`. El horario de fin y el precio los calcula el servidor. */
export const cuerpoReservaManual = (valores) => ({
  cancha: Number(valores.cancha),
  fecha_turno: valores.fecha_turno,
  hora_inicio: valores.hora_inicio,
  nombre_cliente_manual: valores.nombre_cliente_manual.trim(),
  telefono_cliente_manual: valores.telefono_cliente_manual.trim(),
  observaciones: valores.observaciones.trim(),
});
