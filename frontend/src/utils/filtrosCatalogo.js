import { COBERTURA, ORDENES_CATALOGO, VISTA_LISTA, VISTA_MAPA } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';

export const FILTROS_VACIOS = Object.freeze({
  deporte: '',
  cobertura: '',
  servicios: Object.freeze([]),
  search: '',
  ordering: '',
});

const ES_ID = /^[1-9]\d{0,9}$/;
const ORDENES = new Set(ORDENES_CATALOGO.map(({ valor }) => valor));

/**
 * Filtros del catálogo a partir de los parámetros de la URL. Lo que no es válido se descarta: un enlace armado a
 * mano nunca produce una consulta que el backend rechace.
 */
export const leerFiltros = (parametros) => {
  const deporte = parametros.get('deporte') ?? '';
  const cobertura = parametros.get('cobertura') ?? '';
  const ordering = parametros.get('ordering') ?? '';
  return {
    deporte: ES_ID.test(deporte) ? deporte : '',
    cobertura: Object.hasOwn(COBERTURA, cobertura) ? cobertura : '',
    servicios: [...new Set(parametros.getAll('servicio').filter((id) => ES_ID.test(id)))],
    search: (parametros.get('search') ?? '').trim().slice(0, PARAMETROS.limitesCampos.busqueda),
    ordering: ORDENES.has(ordering) ? ordering : '',
  };
};

/** Parámetros de consulta (y de la URL) de los filtros activos; `servicio` se repite una vez por cada elegido. */
export const aParametros = (filtros) => {
  const parametros = new URLSearchParams();
  if (filtros.deporte) parametros.set('deporte', filtros.deporte);
  if (filtros.cobertura) parametros.set('cobertura', filtros.cobertura);
  filtros.servicios.forEach((id) => parametros.append('servicio', id));
  const busqueda = filtros.search.trim();
  if (busqueda) parametros.set('search', busqueda);
  if (filtros.ordering) parametros.set('ordering', filtros.ordering);
  return parametros;
};

/** Cantidad de criterios de filtrado activos; el orden no filtra, así que no cuenta. */
export const contarFiltros = (filtros) => (
  Number(Boolean(filtros.deporte)) + Number(Boolean(filtros.cobertura)) + filtros.servicios.length
  + Number(Boolean(filtros.search.trim()))
);

/** Hay algo para limpiar: algún filtro o un orden distinto del de origen. */
export const hayFiltros = (filtros) => contarFiltros(filtros) > 0 || Boolean(filtros.ordering);

/** Vista elegida en la URL: el mapa solo si lo pide `?vista=mapa`; cualquier otro valor es la lista. */
export const leerVista = (parametros) => (parametros.get('vista') === VISTA_MAPA ? VISTA_MAPA : VISTA_LISTA);

/** Parámetros de la URL con la vista agregada; la lista es la vista de origen y no se escribe. */
export const conVista = (parametros, vista) => {
  if (vista === VISTA_MAPA) parametros.set('vista', VISTA_MAPA);
  return parametros;
};
