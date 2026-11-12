import { ENTORNO, PARAMETROS } from '../config/parametros.js';

/**
 * Registra el service worker (`public/sw.js`) solo en el build de producción: en desarrollo interferiría con el
 * recargado en caliente de Vite. Se espera a `load` para que el registro no compita con la carga inicial. Un fallo
 * (navegador sin soporte, contexto no seguro) no afecta a la aplicación, que funciona igual sin él.
 */
export const registrarServiceWorker = () => {
  if (!ENTORNO.produccion || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(PARAMETROS.pwa.rutaServiceWorker, { scope: '/' }).catch(() => {});
  });
};
