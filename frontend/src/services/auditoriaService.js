/** Registro de eventos de seguridad y de negocio (superadmin). */
import { aParametrosAuditoria } from '../utils/sistema.js';
import { apiDjango } from './api.js';

/** Una página del registro, del evento más reciente al más antiguo, con los filtros activos. */
export const listarAuditoria = async (filtros, pagina, signal) => {
  const { data } = await apiDjango.get('/api/auditoria/', { params: aParametrosAuditoria(filtros, pagina), signal });
  return data;
};
