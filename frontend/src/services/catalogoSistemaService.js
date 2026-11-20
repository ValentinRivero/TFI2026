/**
 * Catálogos de deportes y servicios vistos por el superadmin: incluyen los dados de baja y cuántos registros vigentes
 * usa cada ítem. La baja es lógica y el backend la rechaza (400) mientras el ítem esté en uso; ese mensaje se muestra
 * tal cual. `recurso` es una clave de `CATALOGOS_SISTEMA` (`deportes` o `servicios`).
 */
import { REGISTRO_ACTIVO } from '../config/catalogos.js';
import { CATALOGOS_SISTEMA } from '../utils/catalogoSistema.js';
import { apiDjango } from './api.js';

const rutaDe = (recurso) => {
  const catalogo = CATALOGOS_SISTEMA[recurso];
  if (!catalogo) throw new Error(`Catálogo desconocido: ${recurso}`);
  return catalogo.ruta;
};

const rutaDeItem = (recurso, id) => `${rutaDe(recurso)}${encodeURIComponent(id)}/`;

/** Todos los ítems del catálogo (colección acotada: no se pagina), activos y de baja. */
export const listarCatalogoSistema = async (recurso, signal) => {
  const { data } = await apiDjango.get(rutaDe(recurso), { signal });
  return data;
};

export const crearItemCatalogo = async (recurso, nombre) => {
  const { data } = await apiDjango.post(rutaDe(recurso), { nombre });
  return data;
};

export const renombrarItemCatalogo = async (recurso, id, nombre) => {
  const { data } = await apiDjango.patch(rutaDeItem(recurso, id), { nombre });
  return data;
};

/** Devuelve un ítem dado de baja al catálogo. */
export const reactivarItemCatalogo = async (recurso, id) => {
  const { data } = await apiDjango.patch(rutaDeItem(recurso, id), { estado: REGISTRO_ACTIVO });
  return data;
};

/** Baja lógica: responde 204 sin cuerpo. */
export const darDeBajaItemCatalogo = async (recurso, id) => {
  await apiDjango.delete(rutaDeItem(recurso, id));
};

/**
 * Una página de dónde está en uso un ítem, con los mismos criterios que bloquean su baja. Deportes: complejos con sus
 * canchas (`{ complejo_id, complejo_nombre, canchas }`); servicios: complejos (`{ complejo_id, complejo_nombre }`).
 */
export const listarUsosCatalogo = async (recurso, id, pagina, signal) => {
  const { data } = await apiDjango.get(`${rutaDeItem(recurso, id)}usos/`, { params: { page: pagina }, signal });
  return data;
};
