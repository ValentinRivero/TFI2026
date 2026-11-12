/**
 * Turnos fijos del complejo: reservas recurrentes de un cliente en un día y horario. El cambio de horario pide
 * confirmación (`409` con `requiere_confirmacion`); las fechas puntuales se llevan a la agenda con `fechas/`.
 */
import { aParametrosEnEspera, aParametrosTurnosFijos } from '../utils/turnosFijos.js';
import { apiDjango } from './api.js';

const ruta = (id) => `/api/turnos-fijos/${encodeURIComponent(id)}/`;

/** Una página de los turnos fijos vigentes y pausados del complejo, con los filtros activos. */
export const listarTurnosFijos = async (complejoId, filtros, pagina, signal) => {
  const { data } = await apiDjango.get('/api/turnos-fijos/', {
    params: aParametrosTurnosFijos(complejoId, filtros, pagina),
    signal,
  });
  return data;
};

/** Una página de los turnos fijos con fechas en espera por una excepción horaria. */
export const listarTurnosEnEspera = async (complejoId, pagina, signal) => {
  const { data } = await apiDjango.get('/api/turnos-fijos/', {
    params: aParametrosEnEspera(complejoId, pagina),
    signal,
  });
  return data;
};

export const crearTurnoFijo = async (cuerpo) => {
  const { data } = await apiDjango.post('/api/turnos-fijos/', cuerpo);
  return data;
};

/** Pausa o reanuda (`estado`), extiende la vigencia o cambia el horario (con `confirmar`). */
export const actualizarTurnoFijo = async (id, datos) => {
  const { data } = await apiDjango.patch(ruta(id), datos);
  return data;
};

/** Baja lógica: no cancela las fechas que ya se registraron en la agenda. */
export const darDeBajaTurnoFijo = async (id) => {
  await apiDjango.delete(ruta(id));
};

/** Lleva una fecha del turno fijo a la agenda: `accion` `mantener` (confirmada) o `cancelar` (cancelada por el complejo). */
export const registrarFechaTurnoFijo = async (id, fechaTurno, accion) => {
  const { data } = await apiDjango.post(`${ruta(id)}fechas/`, { fecha_turno: fechaTurno, accion });
  return data;
};
