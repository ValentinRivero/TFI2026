import { useState } from 'react';
import { MOTIVO_RECHAZO_TRANSFERENCIA } from '../config/catalogos.js';
import { rechazarTransferencia } from '../services/reservaService.js';
import { errorDeNotaRechazo } from '../utils/pagos.js';
import useEnvio from './useEnvio.js';

const MOTIVO_INICIAL = String(Object.keys(MOTIVO_RECHAZO_TRANSFERENCIA)[0]);

/**
 * Rechazo de la transferencia que informó el jugador, desde la agenda: un motivo de la lista y una nota corta
 * opcional que verá el jugador. `abrir(reserva)` abre el diálogo; `guardar` envía y, si sale bien, llama a
 * `alGuardar`. Un rechazo del servidor (la seña ya se confirmó, ya estaba rechazada) queda dentro del diálogo y
 * `alError` permite recargar la lista para mostrar el estado real.
 */
export default function useRechazarTransferencia({ alGuardar, alError }) {
  const [edicion, setEdicion] = useState(null);
  const envio = useEnvio();

  const abrir = (reserva) => {
    envio.limpiar();
    setEdicion({ reserva, motivo: MOTIVO_INICIAL, nota: '' });
  };

  const cerrar = () => {
    envio.limpiar();
    setEdicion(null);
  };

  const cambiar = (campo, valor) => {
    envio.limpiar();
    setEdicion((actual) => ({ ...actual, [campo]: valor }));
  };

  const errorNota = edicion ? errorDeNotaRechazo(edicion.nota) : undefined;

  const guardar = async () => {
    if (!edicion || errorNota) return;
    const resultado = await envio.enviar(() => rechazarTransferencia(edicion.reserva.id, {
      motivo: Number(edicion.motivo),
      nota: edicion.nota.trim(),
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
    motivo: edicion?.motivo ?? MOTIVO_INICIAL,
    nota: edicion?.nota ?? '',
    errorNota,
    error: envio.error,
    enviando: envio.enviando,
    abrir,
    cerrar,
    cambiar,
    guardar,
  };
}
