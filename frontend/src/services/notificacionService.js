import { NOTIFICACION_LEIDA, NOTIFICACION_NO_LEIDA } from '../config/catalogos.js';
import { aParametrosApi, normalizarNotificacion, normalizarPagina } from '../utils/notificaciones.js';
import { apiNode } from './api.js';

const RUTA = '/api/actividad/notificaciones';

/**
 * Una página de las notificaciones dirigidas a la cuenta (`{ count, next, previous, results }`). Cada rol recibe las
 * suyas en esta bandeja: el personal de un complejo, lo operativo; el dueño, además lo comercial; el superadmin, lo del sistema.
 */
export const listarMisNotificaciones = async (filtros, pagina, signal) => {
  const { data } = await apiNode.get(`${RUTA}/mias`, { params: aParametrosApi(filtros, pagina), signal });
  return normalizarPagina(data);
};

/**
 * Una página del registro del complejo (dueño, operador y superadmin): lo ocurrido, sin estado de lectura. El operador
 * no recibe lo comercial; lo decide el servicio.
 */
export const listarRegistroDelComplejo = async (complejoId, filtros, pagina, signal) => {
  const { data } = await apiNode.get(RUTA, {
    params: { ...aParametrosApi({ ...filtros, complejo: '' }, pagina), complejo_id: complejoId },
    signal,
  });
  return normalizarPagina(data);
};

/** Cantidad de notificaciones propias sin leer: pide una sola fila y lee el total de la paginación. */
export const contarMisNoLeidas = async (signal) => {
  const { data } = await apiNode.get(`${RUTA}/mias`, { params: { estado: NOTIFICACION_NO_LEIDA, limit: 1 }, signal });
  return data?.count ?? 0;
};

/** Marca como leídas, en una sola operación, todas las notificaciones sin leer de la cuenta. Responde cuántas fueron. */
export const marcarTodasMisNotificacionesLeidas = async () => {
  const { data } = await apiNode.patch(`${RUTA}/mias/leidas`);
  return data?.actualizadas ?? 0;
};

/** Marca una notificación como leída. Responde la notificación actualizada. */
export const marcarNotificacionLeida = async (id) => {
  const { data } = await apiNode.patch(`${RUTA}/${encodeURIComponent(id)}`, { estado: NOTIFICACION_LEIDA });
  return normalizarNotificacion(data);
};
