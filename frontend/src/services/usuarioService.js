/** Cuentas de usuario vistas por el superadmin: listado con filtros y edición de datos, rol y estado. */
import { aParametrosUsuarios } from '../utils/sistema.js';
import { apiDjango } from './api.js';

/** Una página de cuentas con los filtros activos (ver `utils/sistema.js`). */
export const listarUsuarios = async (filtros, pagina, signal) => {
  const { data } = await apiDjango.get('/api/usuarios/', { params: aParametrosUsuarios(filtros, pagina), signal });
  return data;
};

/**
 * Primera página de cuentas activas con rol de dueño que coinciden con la búsqueda, para elegir el propietario de un
 * complejo nuevo. El listado completo no se descarga: se acota escribiendo parte del nombre o del correo.
 */
export const buscarDuenos = async (busqueda, signal) => {
  const { data } = await apiDjango.get('/api/usuarios/', {
    params: aParametrosUsuarios({ rol: 'DUENO_COMPLEJO', estado: '1', busqueda }, 1),
    signal,
  });
  return data.results ?? [];
};

const ruta = (id) => `/api/usuarios/${encodeURIComponent(id)}/`;

/** Una cuenta por id, siempre desde el servidor (la ficha completa). */
export const obtenerUsuario = async (id, signal) => {
  const { data } = await apiDjango.get(ruta(id), { signal });
  return data;
};

// Resúmenes ya consultados, por id de usuario: pasar el mouse por el mismo usuario de la auditoría no vuelve a pedirlo.
// Solo se guardan respuestas correctas, y editar la cuenta descarta su entrada.
const resumenes = new Map();

/** Cuenta para el resumen emergente de la auditoría: la pide una sola vez por id mientras la pestaña siga abierta. */
export const obtenerResumenUsuario = async (id, signal) => {
  if (resumenes.has(id)) return resumenes.get(id);
  const usuario = await obtenerUsuario(id, signal);
  resumenes.set(id, usuario);
  return usuario;
};

/**
 * Edita los campos enviados. El backend rechaza (400) dejar al sistema sin superadmin activo o quitar el rol de
 * dueño a quien tiene contratos vigentes; esos mensajes se muestran tal cual.
 */
export const actualizarUsuario = async (id, datos) => {
  const { data } = await apiDjango.patch(ruta(id), datos);
  resumenes.delete(id);
  return data;
};
