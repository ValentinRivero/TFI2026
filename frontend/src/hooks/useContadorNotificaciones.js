import { useEffect, useState } from 'react';
import { PARAMETROS } from '../config/parametros.js';
import { contarMisNoLeidas } from '../services/notificacionService.js';
import { alMarcarLeida } from '../utils/avisosNotificaciones.js';
import { ajustarContador, debeSondear } from '../utils/notificaciones.js';

/**
 * Cantidad de notificaciones propias sin leer para la campana de la barra. Consulta al montar y cada
 * `PARAMETROS.notificaciones.sondeoMs`, se pausa con la pestaña oculta y se actualiza al volver a verla. Cuando la
 * bandeja marca una notificación como leída, descuenta el contador en el acto y confirma con el servidor.
 *
 * Si `backend-node` no responde conserva el último valor y no muestra errores: la campana nunca rompe la barra.
 * Sin `usuarioId` (sin sesión) devuelve `null`; el valor de una sesión anterior nunca se atribuye a la siguiente.
 */
export default function useContadorNotificaciones(usuarioId) {
  const [estado, setEstado] = useState({ de: null, valor: null });

  useEffect(() => {
    if (!usuarioId) return undefined;
    const controlador = new AbortController();

    const refrescar = async () => {
      try {
        const total = await contarMisNoLeidas(controlador.signal);
        if (!controlador.signal.aborted) setEstado({ de: usuarioId, valor: total });
      } catch {
        // Falla en silencio: se mantiene el último valor conocido hasta el próximo intento.
      }
    };
    const consultar = () => {
      if (debeSondear(document.visibilityState)) refrescar();
    };

    consultar();
    const intervalo = setInterval(consultar, PARAMETROS.notificaciones.sondeoMs);
    document.addEventListener('visibilitychange', consultar);
    const dejarDeEscuchar = alMarcarLeida(() => {
      setEstado((previo) => (previo.de === usuarioId ? { de: usuarioId, valor: ajustarContador(previo.valor, -1) } : previo));
      refrescar();
    });

    return () => {
      controlador.abort();
      clearInterval(intervalo);
      document.removeEventListener('visibilitychange', consultar);
      dejarDeEscuchar();
    };
  }, [usuarioId]);

  return usuarioId && estado.de === usuarioId ? estado.valor : null;
}
