/** Excepciones horarias (cierres por mantenimiento, clima, feriados...) de un complejo o de una de sus canchas. */
import { aParametrosExcepciones } from '../utils/excepciones.js';
import { apiDjango } from './api.js';

/** Una página de excepciones del complejo con los filtros activos (ver `utils/excepciones.js`). */
export const listarExcepciones = async (complejoId, filtros, pagina, signal) => {
  const { data } = await apiDjango.get('/api/excepciones/', {
    params: aParametrosExcepciones(complejoId, filtros, pagina),
    signal,
  });
  return data;
};

/** Alta de una excepción. No se edita: una mal cargada se da de baja y se registra otra. */
export const crearExcepcion = async (cuerpo) => {
  const { data } = await apiDjango.post('/api/excepciones/', cuerpo);
  return data;
};

/** Baja lógica de la excepción. */
export const darDeBajaExcepcion = async (id) => {
  await apiDjango.delete(`/api/excepciones/${encodeURIComponent(id)}/`);
};
