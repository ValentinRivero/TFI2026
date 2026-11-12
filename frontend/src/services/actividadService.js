import { apiNode } from './api.js';

/**
 * Informa a `backend-node` una visita o una consulta de grilla. Es una métrica secundaria: nunca bloquea la pantalla
 * ni propaga errores. Devuelve `true` si se registró y `false` si no (Node caído, límite de peticiones, etc.).
 * El usuario no se envía: Node lo toma del token, si hay sesión.
 */
export const registrarActividad = async (tipoEvento, complejoId, metadata) => {
  try {
    await apiNode.post('/api/actividad', {
      tipo_evento: tipoEvento,
      complejo_id: Number(complejoId),
      ...(metadata ? { metadata } : {}),
    });
    return true;
  } catch {
    return false;
  }
};
