import { useCallback, useState } from 'react';

const INICIAL = Object.freeze({ enviando: false, error: null, exito: false });

/**
 * Estado de una acción que escribe en el backend (guardar, dar de baja). `enviar(accion)` ejecuta la promesa que
 * devuelve `accion` y responde `{ ok: true, resultado }` o `{ ok: false, error }`: nunca lanza, así el que llama
 * decide qué hacer con cada falla (por ejemplo, abrir una confirmación ante un 409).
 */
export default function useEnvio() {
  const [estado, setEstado] = useState(INICIAL);

  const enviar = useCallback(async (accion) => {
    setEstado({ enviando: true, error: null, exito: false });
    try {
      const resultado = await accion();
      setEstado({ enviando: false, error: null, exito: true });
      return { ok: true, resultado };
    } catch (error) {
      setEstado({ enviando: false, error, exito: false });
      return { ok: false, error };
    }
  }, []);

  const limpiar = useCallback(() => setEstado(INICIAL), []);

  return { ...estado, enviar, limpiar };
}
