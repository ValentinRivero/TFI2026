import { useState } from 'react';
import useEnvio from './useEnvio.js';

/**
 * Acción que pide confirmación antes de ejecutarse (dar de baja, cancelar). `pedir(objetivo)` abre el diálogo para ese
 * elemento; `confirmar` ejecuta `ejecutar(objetivo)` y, si sale bien, cierra y llama a `alExito(objetivo, resultado)`.
 * Si falla, el diálogo queda abierto con `error` para reintentar o cancelar, y se llama a `alError(error)` (por
 * ejemplo, para recargar la lista ante un 404).
 */
export default function useConfirmacion(ejecutar, { alExito, alError } = {}) {
  const [objetivo, setObjetivo] = useState(null);
  const envio = useEnvio();

  const pedir = (elemento) => {
    envio.limpiar();
    setObjetivo(elemento);
  };

  const cerrar = () => {
    envio.limpiar();
    setObjetivo(null);
  };

  const confirmar = async () => {
    if (objetivo === null) return;
    const resultado = await envio.enviar(() => ejecutar(objetivo));
    if (!resultado.ok) {
      alError?.(resultado.error);
      return;
    }
    setObjetivo(null);
    alExito?.(objetivo, resultado.resultado);
  };

  return { objetivo, error: envio.error, pedir, cerrar, confirmar };
}
