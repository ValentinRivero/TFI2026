/**
 * Catálogo público de complejos, su detalle, la grilla de un día y los catálogos de filtros. Absorbe la diferencia
 * entre listas paginadas (`{ results }`) y listas completas (arreglo) para que las pantallas reciban siempre lo mismo.
 */
import { aParametros } from '../utils/filtrosCatalogo.js';
import { apiDjango } from './api.js';

const comoLista = (datos) => (Array.isArray(datos) ? datos : (datos?.results ?? []));

/** Una página del catálogo (`{ count, next, previous, results }`) con los filtros activos. */
export const listarComplejos = async (filtros, pagina, signal) => {
  const params = aParametros(filtros);
  params.set('page', String(pagina));
  const { data } = await apiDjango.get('/api/complejos/', { params, signal });
  return data;
};

/** Puntos del mapa con los mismos filtros del catálogo: lista completa y sin paginar, con tope en el backend. */
export const listarMarcadores = async (filtros, signal) => {
  const { data } = await apiDjango.get('/api/complejos/marcadores/', { params: aParametros(filtros), signal });
  return comoLista(data);
};

export const obtenerComplejo = async (id, signal) => {
  const { data } = await apiDjango.get(`/api/complejos/${encodeURIComponent(id)}/`, { signal });
  return data;
};

/** Grilla de un día (`AAAA-MM-DD`). Un 404 significa que el complejo ya no está habilitado. */
export const obtenerGrilla = async (id, fecha, signal) => {
  const { data } = await apiDjango.get(`/api/complejos/${encodeURIComponent(id)}/grilla/`, {
    params: { fecha },
    signal,
  });
  return data;
};

export const listarDeportes = async (signal) => {
  const { data } = await apiDjango.get('/api/deportes/', { signal });
  return comoLista(data);
};

export const listarServicios = async (signal) => {
  const { data } = await apiDjango.get('/api/servicios/', { signal });
  return comoLista(data);
};
