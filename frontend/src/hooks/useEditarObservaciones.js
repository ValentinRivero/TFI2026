import { useState } from 'react';
import { actualizarReservaAgenda } from '../services/reservaService.js';
import { errorDeObservaciones, observacionesModificadas } from '../utils/agenda.js';
import useEnvio from './useEnvio.js';

/**
 * Edición de las observaciones internas de una reserva de la agenda, en cualquier estado. `abrir(reserva)` parte del
 * texto guardado; `guardar` envía solo si hubo cambios y el texto es válido, y al terminar llama a `alGuardar`. Un
 * rechazo del servidor queda en `error` dentro del diálogo, y `alError` permite recargar la lista ante un 404.
 */
export default function useEditarObservaciones({ alGuardar, alError }) {
  const [edicion, setEdicion] = useState(null);
  const envio = useEnvio();

  const abrir = (reserva) => {
    envio.limpiar();
    setEdicion({ reserva, texto: reserva.observaciones ?? '' });
  };

  const cerrar = () => {
    envio.limpiar();
    setEdicion(null);
  };

  const cambiar = (texto) => {
    envio.limpiar();
    setEdicion((actual) => ({ ...actual, texto }));
  };

  const errorLocal = edicion ? errorDeObservaciones(edicion.texto) : undefined;
  const hayCambios = edicion ? observacionesModificadas(edicion.reserva, edicion.texto) : false;

  const guardar = async () => {
    if (!edicion || errorLocal || !hayCambios) return;
    const resultado = await envio.enviar(() => actualizarReservaAgenda(edicion.reserva.id, {
      observaciones: edicion.texto.trim(),
    }));
    if (resultado.ok) {
      setEdicion(null);
      alGuardar?.(resultado.resultado);
    } else {
      alError?.(resultado.error);
    }
  };

  return {
    reserva: edicion?.reserva ?? null,
    texto: edicion?.texto ?? '',
    errorLocal,
    error: envio.error,
    enviando: envio.enviando,
    hayCambios,
    abrir,
    cerrar,
    cambiar,
    guardar,
  };
}
