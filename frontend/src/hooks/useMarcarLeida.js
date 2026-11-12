import { marcarNotificacionLeida } from '../services/notificacionService.js';
import useEnvio from './useEnvio.js';

/**
 * Marca notificaciones como leídas. `marcar(notificacion)` devuelve una promesa que nunca rechaza (la usa
 * `BotonAccion` para evitar el doble clic) y, si el servidor confirma, llama a `alMarcar(notificacion)`. Un fallo
 * queda en `error` hasta que se descarta.
 */
export default function useMarcarLeida({ alMarcar }) {
  const { error, enviar, limpiar } = useEnvio();

  const marcar = async (notificacion) => {
    const resultado = await enviar(() => marcarNotificacionLeida(notificacion.id));
    if (resultado.ok) alMarcar?.(notificacion);
  };

  return { marcar, error, descartarError: limpiar };
}
