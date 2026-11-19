/** Dashboard estadístico de un complejo en un rango de fechas (dueño y superadmin). */
import { aParametrosReporte } from '../utils/reportes.js';
import { apiDjango } from './api.js';

/**
 * Recaudación, conteos por estado, ocupación por cancha y ranking de horarios. Con `criterio` distinto del día de
 * juego, `ocupacion` llega en `null`. Un rango inválido responde 400.
 */
export const obtenerDashboard = async (complejoId, filtros, signal) => {
  const { data } = await apiDjango.get('/api/reportes/dashboard/', {
    params: aParametrosReporte(complejoId, filtros),
    signal,
  });
  return data;
};
