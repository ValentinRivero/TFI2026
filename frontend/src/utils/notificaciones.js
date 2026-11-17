import {
  CATEGORIA_NOTIFICACION,
  FILTRO_ESTADO_NOTIFICACION,
  NOTIFICACION_LEIDA,
  PRIORIDAD_NOTIFICACION,
  PRIORIDAD_URGENTE,
} from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';

const FILTROS_DE_ESTADO = Object.values(FILTRO_ESTADO_NOTIFICACION);
const ID_DE_COMPLEJO = /^[1-9]\d*$/;

export const ESTADO_FILTRO_POR_DEFECTO = FILTRO_ESTADO_NOTIFICACION.NO_LEIDAS.valor;

/** Avisos urgentes pendientes: bloque fijo de la bandeja, independiente de los filtros elegidos. */
export const FILTROS_URGENTES = Object.freeze({
  estado: ESTADO_FILTRO_POR_DEFECTO,
  prioridad: String(PRIORIDAD_URGENTE),
  categoria: '',
  complejo: '',
});

/** Filtros del registro de un complejo: todas las entradas, sin estado de lectura ni complejo (lo fija la pantalla). */
export const filtrosDeRegistro = (filtros) => ({ ...filtros, estado: 'todas', complejo: '' });

/** Los urgentes pendientes del mismo complejo que la bandeja: el único filtro que comparten. */
export const filtrosUrgentesDe = (filtros) => ({ ...FILTROS_URGENTES, complejo: filtros.complejo });

// Un código que el catálogo no conoce (por ejemplo, de un enlace editado a mano) se ignora.
const codigoDe = (valor, catalogo) => (valor !== null && Object.hasOwn(catalogo, valor) ? valor : '');

/** Filtros de una bandeja a partir de la query de la URL; lo que no es válido vuelve al valor por defecto. */
export const leerFiltros = (parametros) => {
  const estado = FILTROS_DE_ESTADO.find(({ valor }) => valor === parametros.get('estado'));
  return {
    estado: estado?.valor ?? ESTADO_FILTRO_POR_DEFECTO,
    prioridad: codigoDe(parametros.get('prioridad'), PRIORIDAD_NOTIFICACION),
    categoria: codigoDe(parametros.get('categoria'), CATEGORIA_NOTIFICACION),
    // Un id de complejo: cualquier otra cosa (por ejemplo, de un enlace editado a mano) se ignora.
    complejo: ID_DE_COMPLEJO.test(parametros.get('complejo') ?? '') ? parametros.get('complejo') : '',
  };
};

/** Query de la URL con solo los filtros que se apartan de los valores por defecto. */
export const aParametrosUrl = (filtros) => {
  const parametros = {};
  if (filtros.estado !== ESTADO_FILTRO_POR_DEFECTO) parametros.estado = filtros.estado;
  if (filtros.prioridad) parametros.prioridad = filtros.prioridad;
  if (filtros.categoria) parametros.categoria = filtros.categoria;
  if (filtros.complejo) parametros.complejo = filtros.complejo;
  return parametros;
};

/** Parámetros de la bandeja propia de `backend-node`; `complejo` acota a los avisos de un solo complejo. */
export const aParametrosApi = (filtros, pagina = 1) => {
  const parametros = {};
  if (filtros.complejo) parametros.complejo_id = filtros.complejo;
  const codigoEstado = FILTROS_DE_ESTADO.find(({ valor }) => valor === filtros.estado)?.codigo;
  if (codigoEstado) parametros.estado = codigoEstado;
  if (filtros.categoria) parametros.categoria = filtros.categoria;
  if (filtros.prioridad) parametros.prioridad = filtros.prioridad;
  if (pagina > 1) parametros.page = pagina;
  return parametros;
};

/** Node serializa `id`; se admite también `_id` por si una respuesta llega sin transformar. */
export const normalizarNotificacion = (notificacion) => ({
  ...notificacion,
  id: String(notificacion.id ?? notificacion._id ?? ''),
});

/** Página `{ count, next, previous, results }` de Node con cada notificación normalizada. */
export const normalizarPagina = (pagina) => ({
  count: pagina?.count ?? 0,
  next: pagina?.next ?? null,
  previous: pagina?.previous ?? null,
  results: (pagina?.results ?? []).map(normalizarNotificacion),
});

export const esUrgente = (notificacion) => notificacion.prioridad === PRIORIDAD_URGENTE;

/**
 * Refleja en una lista cargada las notificaciones recién marcadas como leídas: las pasa a leídas o, si la bandeja
 * muestra solo no leídas, las oculta.
 */
export const aplicarLeidas = (notificaciones, idsLeidos, ocultar) => {
  if (idsLeidos.length === 0) return notificaciones;
  const marcadas = new Set(idsLeidos);
  if (ocultar) return notificaciones.filter(({ id }) => !marcadas.has(id));
  return notificaciones.map((notificacion) => (
    marcadas.has(notificacion.id) ? { ...notificacion, estado: NOTIFICACION_LEIDA } : notificacion
  ));
};

/**
 * Claves de texto del estado vacío de una bandeja según los filtros: con categoría, prioridad o complejo elegidos se sugiere
 * ampliar la búsqueda; sin ellas y viendo solo las no leídas, que no hay pendientes; en otro caso, el texto propio
 * de la bandeja (`claveDescripcion`).
 */
export const clavesDeVacio = (filtros, claveDescripcion) => {
  if (filtros.categoria || filtros.prioridad || filtros.complejo) {
    return { titulo: 'notificaciones.vacioTitulo', descripcion: 'notificaciones.vacioFiltradasDescripcion' };
  }
  if (filtros.estado === ESTADO_FILTRO_POR_DEFECTO) {
    return { titulo: 'notificaciones.vacioNoLeidasTitulo', descripcion: 'notificaciones.vacioNoLeidasDescripcion' };
  }
  return { titulo: 'notificaciones.vacioTitulo', descripcion: claveDescripcion };
};

/** Suma `delta` al contador de la campana sin bajar de cero; un contador desconocido (`null`) sigue desconocido. */
export const ajustarContador = (actual, delta) => (actual === null ? null : Math.max(0, actual + delta));

/** Texto del badge de la campana: el número, o "99+" desde el tope configurado. */
export const textoContador = (cantidad, tope = PARAMETROS.notificaciones.contadorMaximo) => (
  cantidad > tope ? `${tope}+` : String(cantidad)
);

/** El sondeo de la campana se pausa mientras la pestaña está oculta. */
export const debeSondear = (visibilidad) => visibilidad !== 'hidden';
