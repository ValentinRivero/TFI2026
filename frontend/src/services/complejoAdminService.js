/**
 * Administración del complejo propio: complejos que el usuario administra, su configuración comercial, los
 * servicios que ofrece y sus operadores. El acceso lo decide el backend (dueño, operador o superadmin).
 */
import { apiDjango } from './api.js';
import { traerTodasLasPaginas } from './paginasService.js';

const ruta = (id) => `/api/complejos/${encodeURIComponent(id)}`;

/** Todos los complejos que el usuario administra (colección acotada: un dueño tiene pocos). */
export const listarAdministrados = (signal) => traerTodasLasPaginas(async (pagina) => {
  const { data } = await apiDjango.get('/api/complejos/administrados/', { params: { page: pagina }, signal });
  return data;
});

/** Cambia solo los campos enviados. Devuelve el complejo completo ya actualizado. */
export const actualizarConfiguracion = async (id, datos) => {
  const { data } = await apiDjango.patch(`${ruta(id)}/`, datos);
  return data;
};

/** Deja activos exactamente los servicios indicados (ids). Devuelve `{ servicios: [{ id, nombre }] }`. */
export const sincronizarServicios = async (id, servicios) => {
  const { data } = await apiDjango.put(`${ruta(id)}/servicios/`, { servicios });
  return data;
};

/** Una página de los operadores vinculados al complejo. */
export const listarOperadores = async (id, pagina, signal) => {
  const { data } = await apiDjango.get(`${ruta(id)}/operadores/`, { params: { page: pagina }, signal });
  return data;
};

/** Vincula una cuenta de operador por su email exacto. */
export const vincularOperador = async (id, email) => {
  const { data } = await apiDjango.post(`${ruta(id)}/operadores/`, { email });
  return data;
};

/** Desvincula al operador: la cuenta sigue activa pero deja de administrar el complejo. */
export const desvincularOperador = async (id, usuarioId) => {
  await apiDjango.delete(`${ruta(id)}/operadores/${encodeURIComponent(usuarioId)}/`);
};
