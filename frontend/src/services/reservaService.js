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
