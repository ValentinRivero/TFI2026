import { PARAMETROS } from '../config/parametros.js';

/** Cantidad de páginas de una lista paginada del backend. Siempre hay al menos una. */
export const totalDePaginas = (cantidad, tamanio = PARAMETROS.paginacion.tamanio) => (
  Math.max(1, Math.ceil(cantidad / tamanio))
);

/**
 * Números de página que muestra el paginador: la actual y dos a cada lado. Cerca de los extremos se completan hacia
 * el otro lado para mostrar siempre `cantidad` páginas (o todas, si hay menos).
 */
export const ventanaDePaginas = (actual, total, cantidad = PARAMETROS.paginacion.botones) => {
  const cuantas = Math.min(cantidad, total);
  const mitad = Math.floor(cuantas / 2);
  const inicio = Math.min(Math.max(actual - mitad, 1), total - cuantas + 1);
  return Array.from({ length: cuantas }, (_, indice) => inicio + indice);
};
