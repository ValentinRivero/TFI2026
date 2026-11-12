import { useCallback, useSyncExternalStore } from 'react';
import useSesion from './useSesion.js';

/**
 * Complejo elegido en el panel, guardado solo en memoria mientras la pestaña esté abierta: se conserva al pasar entre
 * las subvistas de `/panel/*` y se pierde al recargar la página. Se asocia al usuario que lo eligió, así que una
 * sesión nueva (otra cuenta en la misma pestaña) nunca hereda la selección anterior.
 */
let estado = Object.freeze({ usuarioId: null, complejoId: null });
const oyentes = new Set();

const suscribir = (oyente) => {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
};

const obtenerEstado = () => estado;

const guardar = (usuarioId, complejoId) => {
  estado = Object.freeze({ usuarioId, complejoId });
  oyentes.forEach((oyente) => oyente());
};

/** `{ elegido, elegir }`: id del complejo elegido por el usuario actual (o `null`) y la función para cambiarlo. */
export default function useComplejoActivo() {
  const { usuario } = useSesion();
  const actual = useSyncExternalStore(suscribir, obtenerEstado);
  const usuarioId = usuario?.id ?? null;
  const elegir = useCallback((complejoId) => guardar(usuarioId, complejoId), [usuarioId]);
  return { elegido: actual.usuarioId === usuarioId ? actual.complejoId : null, elegir };
}
