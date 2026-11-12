import { apiNode } from './api.js';

/** Clima actual y pronóstico de los próximos días en el complejo (`backend-node`, con caché de 15 minutos). */
export const obtenerClima = async (complejoId, signal) => {
  const { data } = await apiNode.get(`/api/externa/clima/${encodeURIComponent(complejoId)}`, { signal });
  return data;
};
