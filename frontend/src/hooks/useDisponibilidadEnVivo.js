import { useEffect, useRef } from 'react';
import { PARAMETROS } from '../config/parametros.js';
import { conectarDisponibilidad } from '../services/wsService.js';
import { eventoAfectaGrilla } from '../utils/tiempoReal.js';

/**
 * Mantiene abierto el canal de disponibilidad de un complejo y avisa cuándo volver a pedir la grilla visible.
 * - Los eventos que no afectan la fecha ni las canchas visibles se descartan.
 * - Varios eventos seguidos se agrupan en una sola recarga (ventana `agruparEventosMs`).
 * - Al reconectar después de un corte se recarga de inmediato, porque pudo cambiar algo sin aviso.
 * - Con `habilitado` en falso (por ejemplo, el complejo dejó de estar disponible) se cierra y no se reintenta.
 *
 * La conexión solo se reabre si cambia `complejoId` o `habilitado`; la fecha y las canchas visibles no la tocan. Los
 * cortes se reintentan en silencio, sin mostrar nada al usuario.
 */
export default function useDisponibilidadEnVivo({ complejoId, habilitado, fecha, canchaIds, alRecargar }) {
  const vigente = useRef({ fecha, canchaIds, alRecargar });

  // Los eventos se evalúan con lo último que muestra la pantalla, sin reabrir la conexión al cambiar de día.
  useEffect(() => {
    vigente.current = { fecha, canchaIds, alRecargar };
  });

  useEffect(() => {
    if (!habilitado) return undefined;

    let agrupador = null;
    const recargar = () => vigente.current.alRecargar();

    const conexion = conectarDisponibilidad({
      complejoId,
      alEvento: (evento) => {
        const { fecha: fechaVisible, canchaIds: canchasVisibles } = vigente.current;
        if (!eventoAfectaGrilla(evento, { fecha: fechaVisible, canchaIds: canchasVisibles })) return;
        if (agrupador === null) {
          agrupador = setTimeout(() => {
            agrupador = null;
            recargar();
          }, PARAMETROS.ws.agruparEventosMs);
        }
      },
      alConectar: (reconectada) => {
        if (reconectada) recargar();
      },
    });

    return () => {
      clearTimeout(agrupador);
      conexion.cerrar();
    };
  }, [complejoId, habilitado]);
}
