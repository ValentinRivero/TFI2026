import { useState } from 'react';
import { t } from '../i18n/index.js';
import { cancelarReserva } from '../services/reservaService.js';

const SIN_CANCELACION = Object.freeze({ reserva: null, error: null });

/**
 * Cancelación de una reserva propia con confirmación. `pedir(reserva)` abre el diálogo; `confirmar` cancela y avisa
 * con `aviso`. Si el servidor rechaza (400 por margen vencido, 404), el motivo queda en `error` dentro del diálogo y
 * se recarga la lista para que la fila muestre su estado real. `alCancelar` recarga la lista.
 */
export default function useCancelarReserva({ alCancelar }) {
  const [estado, setEstado] = useState(SIN_CANCELACION);
  const [aviso, setAviso] = useState(null);

  const cerrar = () => setEstado(SIN_CANCELACION);

  const confirmar = async () => {
    const { reserva } = estado;
    if (!reserva) return;
    setEstado({ reserva, error: null });
    try {
      await cancelarReserva(reserva.id);
    } catch (falla) {
      setEstado({ reserva, error: falla });
      if (falla.status === 400 || falla.status === 404) alCancelar();
      return;
    }
    cerrar();
    setAviso(t('misReservas.canceladaOk'));
    alCancelar();
  };

  return {
    reserva: estado.reserva,
    error: estado.error,
    aviso,
    pedir: (reserva) => {
      setAviso(null);
      setEstado({ reserva, error: null });
    },
    cerrar,
    confirmar,
    descartarAviso: () => setAviso(null),
  };
}
