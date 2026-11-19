/** Contratos de los complejos (superadmin): listado, alta de un complejo con su propietario y cambio de estado. */
import { aParametrosContratos } from '../utils/sistema.js';
import { apiDjango } from './api.js';
import { traerTodasLasPaginas } from './paginasService.js';

/** Una página de contratos con los filtros activos (ver `utils/sistema.js`). */
export const listarContratos = async (filtros, pagina, signal) => {
  const { data } = await apiDjango.get('/api/contratos/', { params: aParametrosContratos(filtros, pagina), signal });
  return data;
};

/** Todos los complejos con contrato, para selectores (el sistema administra pocos): hasta el tope de páginas. */
export const listarTodosLosContratos = (signal) => traerTodasLasPaginas((pagina) => (
  listarContratos({ estado: '', busqueda: '', orden: 'nombre' }, pagina, signal)
));

/** Alta de un complejo con su contrato y propietario (un dueño activo). */
export const crearComplejoConContrato = async (cuerpo) => {
  const { data } = await apiDjango.post('/api/contratos/', cuerpo);
  return data;
};

/** Cambia el estado del contrato. Suspendido o baja oculta el complejo del catálogo; activar exige un dueño activo. */
export const cambiarEstadoContrato = async (id, estadoContrato) => {
  const { data } = await apiDjango.patch(`/api/contratos/${encodeURIComponent(id)}/`, { estado_contrato: estadoContrato });
  return data;
};
