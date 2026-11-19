import { aParametrosAgenda } from '../utils/agenda.js';
import { formatearHora } from '../utils/formatos.js';
import { apiDjango } from './api.js';

/** Reserva un turno libre. Un 409 significa que el turno acaba de ocuparse; un 400, que ya no se puede reservar. */
export const crearReserva = async ({ canchaId, fechaTurno, horaInicio }) => {
  const { data } = await apiDjango.post('/api/reservas/', {
    cancha: canchaId,
    fecha_turno: fechaTurno,
    hora_inicio: formatearHora(horaInicio),
  });
  return data;
};

// Las próximas se ordenan de la más cercana a la más lejana y el historial, de la más reciente a la más antigua.
const ORDEN_POR_VIGENCIA = Object.freeze({
  proximas: 'fecha_turno,hora_inicio',
  pasadas: '-fecha_turno,-hora_inicio',
});

/** Una página de las reservas propias (`{ count, next, previous, results }`) de la vista `vigencia`. */
export const listarMisReservas = async (vigencia, pagina, signal) => {
  const { data } = await apiDjango.get('/api/reservas/mias/', {
    params: { vigencia, ordering: ORDEN_POR_VIGENCIA[vigencia], page: pagina },
    signal,
  });
  return data;
};

/** Cancela una reserva propia. Fuera del margen del complejo responde 400 con el motivo. */
export const cancelarReserva = async (id) => {
  const { data } = await apiDjango.post(`/api/reservas/${encodeURIComponent(id)}/cancelar/`);
  return data;
};

// Agenda del complejo: reservas con los datos de contacto de cada cliente (dueño, operador y superadmin).
const rutaAgenda = (id) => `/api/agenda/${encodeURIComponent(id)}/`;

/** Una página de la agenda del complejo con los filtros activos (ver `utils/agenda.js`). */
export const listarAgenda = async (complejoId, filtros, pagina, signal) => {
  const { data } = await apiDjango.get('/api/agenda/', {
    params: aParametrosAgenda(complejoId, filtros, pagina),
    signal,
  });
  return data;
};

/** Reserva telefónica o presencial. Un 409 indica que el turno ya está tomado o cerrado. */
export const crearReservaManual = async (cuerpo) => {
  const { data } = await apiDjango.post('/api/agenda/', cuerpo);
  return data;
};

/** Cambia el estado operativo o las observaciones de una reserva. */
export const actualizarReservaAgenda = async (id, datos) => {
  const { data } = await apiDjango.patch(rutaAgenda(id), datos);
  return data;
};

/** Cancelación por el complejo, sin restricción horaria. */
export const cancelarReservaAgenda = async (id) => {
  const { data } = await apiDjango.post(`${rutaAgenda(id)}cancelar/`);
  return data;
};

/**
 * Reabre una reserva cancelada. Sin `confirmar` el servidor valida el turno y responde `409` con
 * `requiere_confirmacion` y una vista previa; con `confirmar: true` la reserva vuelve a ocupar su turno.
 */
export const reabrirReserva = async (id, estado, confirmar = false) => {
  const { data } = await apiDjango.post(`${rutaAgenda(id)}reabrir/`, { estado, confirmar });
  return data;
};
