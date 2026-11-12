import { PARAMETROS } from '../config/parametros.js';

/**
 * Junta las páginas de una colección chica y acotada por naturaleza (complejos administrados, canchas de un
 * complejo, rangos horarios de una cancha) cuando una pantalla necesita todos sus elementos para un selector o un
 * editor. Se detiene al agotarse las páginas o al llegar al tope de `PARAMETROS.panel.paginasMaximas`.
 */
export const traerTodasLasPaginas = async (pedirPagina, tope = PARAMETROS.panel.paginasMaximas) => {
  const items = [];
  for (let pagina = 1; pagina <= tope; pagina += 1) {
    const datos = await pedirPagina(pagina);
    items.push(...(datos?.results ?? []));
    if (!datos?.next) break;
  }
  return items;
};
