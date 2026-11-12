import { obtenerClima } from '../services/climaService.js';
import useConsulta from './useConsulta.js';

/**
 * Clima de un complejo (`{ datos, error, cargando, recargar }`). Sin `complejoId` todavía (por ejemplo, mientras el
 * catálogo carga el complejo de referencia) no consulta nada y `datos` queda en `null`.
 */
export default function useClima(complejoId) {
  return useConsulta(
    (signal) => (complejoId ? obtenerClima(complejoId, signal) : Promise.resolve(null)),
    [complejoId],
  );
}
