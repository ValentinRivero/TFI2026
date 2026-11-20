/**
 * Roles y permisos vistos por el superadmin. Los roles base (`es_base`) son de solo lectura: el backend rechaza (400)
 * modificarlos o darlos de baja, y también dar de baja un rol que tienen cuentas; esos mensajes se muestran tal cual.
 */
import { REGISTRO_ACTIVO } from '../config/catalogos.js';
import { apiDjango } from './api.js';

const RUTA_ROLES = '/api/sistema/roles/';
const RUTA_PERMISOS = '/api/sistema/permisos/';

const rutaDeRol = (id) => `${RUTA_ROLES}${encodeURIComponent(id)}/`;

/** Todos los roles (colección acotada: no se pagina), activos y de baja, con sus permisos y su cantidad de usos. */
export const listarRoles = async (signal) => {
  const { data } = await apiDjango.get(RUTA_ROLES, { signal });
  return data;
};

/** Catálogo completo de permisos; `asignable: false` marca los exclusivos de la plataforma. */
export const listarPermisos = async (signal) => {
  const { data } = await apiDjango.get(RUTA_PERMISOS, { signal });
  return data;
};

export const crearRol = async (cuerpo) => {
  const { data } = await apiDjango.post(RUTA_ROLES, cuerpo);
  return data;
};

/** Cambia solo los campos enviados; `permisos` reemplaza la lista completa. */
export const actualizarRol = async (id, cuerpo) => {
  const { data } = await apiDjango.patch(rutaDeRol(id), cuerpo);
  return data;
};

export const reactivarRol = async (id) => actualizarRol(id, { estado: REGISTRO_ACTIVO });

/** Baja lógica: responde 204 sin cuerpo. */
export const darDeBajaRol = async (id) => {
  await apiDjango.delete(rutaDeRol(id));
};

/** Una página de las cuentas vigentes (activas o suspendidas) con el rol: `{ id, nombre, email, estado, estado_nombre }`. */
export const listarUsosRol = async (id, pagina, signal) => {
  const { data } = await apiDjango.get(`${rutaDeRol(id)}usos/`, { params: { page: pagina }, signal });
  return data;
};
