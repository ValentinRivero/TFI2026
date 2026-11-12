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

/**
 * Visitas al perfil del complejo y consultas de su grilla en un rango (`fecha_desde` y `fecha_hasta`), en total y por
 * día. Es una métrica de `backend-node`: quien la muestre debe tolerar que falle (502) sin afectar el resto.
 */
export const obtenerVisitas = async (complejoId, fechaDesde, fechaHasta, signal) => {
  const { data } = await apiNode.get('/api/reportes-aux/visitas', {
    params: { complejo_id: complejoId, fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
    signal,
  });
  return data;
};
