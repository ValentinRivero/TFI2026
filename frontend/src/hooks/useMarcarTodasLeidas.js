import { marcarTodasMisNotificacionesLeidas } from '../services/notificacionService.js';
import useEnvio from './useEnvio.js';

/**
 * Marca como leídas todas las notificaciones propias. `marcarTodas()` devuelve una promesa que nunca rechaza (la usa
 * `BotonAccion` para evitar el doble clic) y, si el servidor confirma, llama a `alMarcar(cantidad)`. Un fallo queda
 * en `error` hasta que se descarta.
 */
export default function useMarcarTodasLeidas({ alMarcar }) {
  const { error, enviar, limpiar } = useEnvio();

  const marcarTodas = async () => {
    const resultado = await enviar(marcarTodasMisNotificacionesLeidas);
    if (resultado.ok) alMarcar?.(resultado.resultado);
  };

  return { marcarTodas, error, descartarError: limpiar };
}
