import { LIMITES } from '../config/parametros.js';
import { ErrorHttp } from '../middlewares/errores.middleware.js';
import { parametroUnico } from './validaciones.js';

export const TAMANO_DE_PAGINA = LIMITES.paginacion.tamanoDePagina;
export const MAXIMO_POR_PAGINA = LIMITES.paginacion.maximoPorPagina;

export const validarPaginacion = [
  parametroUnico('page').optional().isInt({ min: 1 }).withMessage('Debe ser un número entero positivo.').toInt(),
  parametroUnico('limit')
    .optional()
    .isInt({ min: 1, max: MAXIMO_POR_PAGINA })
    .withMessage(`Debe ser un número entero entre 1 y ${MAXIMO_POR_PAGINA}.`)
    .toInt(),
];

const enlace = (ruta, filtros, pagina, limite) => `${ruta}?${new URLSearchParams({ ...filtros, page: pagina, limit: limite })}`;

/**
 * Página pedida sobre un total ya contado, con la forma de las listas de Django: `{ count, next, previous }`.
 * Los enlaces son relativos y conservan solo los filtros indicados. Como en Django, la página 1 siempre existe
 * (aunque la lista esté vacía) y una posterior a la última responde 404.
 */
export const paginar = ({ ruta, filtros, pagina = 1, limite = TAMANO_DE_PAGINA, total }) => {
  const paginas = Math.max(1, Math.ceil(total / limite));
  if (pagina > paginas) throw new ErrorHttp(404, 'Página inválida.');
  return {
    salto: (pagina - 1) * limite,
    limite,
    encabezado: {
      count: total,
      next: pagina < paginas ? enlace(ruta, filtros, pagina + 1, limite) : null,
      previous: pagina > 1 ? enlace(ruta, filtros, pagina - 1, limite) : null,
    },
  };
};
