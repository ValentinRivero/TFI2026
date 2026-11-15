import { NOTIFICACION_LEIDA, NOTIFICACION_NO_LEIDA } from '../config/catalogos.js';
import { aParametrosApi, normalizarNotificacion, normalizarPagina } from '../utils/notificaciones.js';
import { apiNode } from './api.js';

const RUTA = '/api/actividad/notificaciones';

/** Una página de las notificaciones dirigidas a la cuenta (`{ count, next, previous, results }`). */
export const listarMisNotificaciones = async (filtros, pagina, signal) => {
  const { data } = await apiNode.get(`${RUTA}/mias`, { params: aParametrosApi(filtros, pagina), signal });
  return normalizarPagina(data);
};

/** Una página de los avisos generales del complejo (dueño, operador y superadmin). */
export const listarNotificacionesDelComplejo = async (complejoId, filtros, pagina, signal) => {
  const { data } = await apiNode.get(RUTA, { params: aParametrosApi(filtros, pagina, complejoId), signal });
  return normalizarPagina(data);
};

/** Cantidad de notificaciones propias sin leer: pide una sola fila y lee el total de la paginación. */
export const contarMisNoLeidas = async (signal) => {
  const { data } = await apiNode.get(`${RUTA}/mias`, { params: { estado: NOTIFICACION_NO_LEIDA, limit: 1 }, signal });
  return data?.count ?? 0;
};

/** Marca una notificación como leída. Responde la notificación actualizada. */
export const marcarNotificacionLeida = async (id) => {
  const { data } = await apiNode.patch(`${RUTA}/${encodeURIComponent(id)}`, { estado: NOTIFICACION_LEIDA });
  return normalizarNotificacion(data);
};
