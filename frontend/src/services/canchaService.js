/**
 * Canchas de un complejo y sus rangos horarios de apertura. Los cambios que dejan reservas o turnos fijos fuera de
 * la grilla responden `409` con `requiere_confirmacion`; se repiten con `confirmar: true` (ver `utils/conflictos.js`).
 */
import { apiDjango } from './api.js';
import { traerTodasLasPaginas } from './paginasService.js';

const rutaCancha = (id) => `/api/canchas/${encodeURIComponent(id)}/`;
const rutaHorario = (id) => `/api/horarios/${encodeURIComponent(id)}/`;

/** Una página de las canchas vigentes del complejo. */
export const listarCanchas = async (complejoId, pagina, signal) => {
  const { data } = await apiDjango.get('/api/canchas/', { params: { complejo: complejoId, page: pagina }, signal });
  return data;
};

/** Todas las canchas del complejo, para selectores (colección acotada por el tamaño de un complejo). */
export const listarTodasLasCanchas = (complejoId, signal) => traerTodasLasPaginas((pagina) => (
  listarCanchas(complejoId, pagina, signal)
));

export const crearCancha = async (datos) => {
  const { data } = await apiDjango.post('/api/canchas/', datos);
  return data;
};

/** Edita los campos enviados. Cambiar la duración o pasarla a mantenimiento puede pedir confirmación (409). */
export const actualizarCancha = async (id, datos) => {
  const { data } = await apiDjango.patch(rutaCancha(id), datos);
  return data;
};

/** Baja lógica. Con reservas o turnos fijos vigentes el backend responde 400 y no admite confirmación. */
export const darDeBajaCancha = async (id) => {
  await apiDjango.delete(rutaCancha(id));
};

/** Todos los rangos de apertura vigentes de una cancha (a lo sumo unos pocos por día de la semana). */
export const listarHorarios = (canchaId, signal) => traerTodasLasPaginas(async (pagina) => {
  const { data } = await apiDjango.get('/api/horarios/', { params: { cancha: canchaId, page: pagina }, signal });
  return data;
});

export const crearHorario = async (canchaId, datos) => {
  const { data } = await apiDjango.post('/api/horarios/', { cancha: canchaId, ...datos });
  return data;
};

/** Edita un rango. Moverlo o acortarlo puede dejar reservas fuera de la grilla y pedir confirmación (409). */
export const actualizarHorario = async (id, datos) => {
  const { data } = await apiDjango.patch(rutaHorario(id), datos);
  return data;
};

/** Baja de un rango. `confirmar` va en la query string porque un DELETE no suele llevar cuerpo. */
export const darDeBajaHorario = async (id, { confirmar = false } = {}) => {
  await apiDjango.delete(rutaHorario(id), { params: confirmar ? { confirmar: true } : undefined });
};
