import { useSyncExternalStore } from 'react';
import { obtenerEstado, suscribir } from '../services/authService.js';

/**
 * Estado de la sesión, sin contexto global: `usuario` (el perfil), `rol` (del token, que se recalcula en cada
 * refresh), `autenticado`, `cargandoSesion` (mientras se recupera la sesión al abrir la app) y
 * `debeAceptarPolitica` (hay una versión nueva de la política de privacidad) y `cierre` (`{ aviso }` si la sesión
 * terminó por una salida deliberada, `null` si no).
 */
export default function useSesion() {
  const { perfil, rol, access, cargandoSesion, cierre } = useSyncExternalStore(suscribir, obtenerEstado);
  return {
    usuario: perfil,
    rol: rol ?? perfil?.rol ?? null,
    autenticado: Boolean(access && perfil),
    cargandoSesion,
    cierre,
    debeAceptarPolitica: Boolean(perfil?.debe_aceptar_politica),
  };
}
