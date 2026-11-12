/**
 * Detección de entorno para la invitación a instalar la aplicación. Son funciones puras: reciben los datos del
 * navegador (`navigator`, `matchMedia`) en lugar de leerlos, así se prueban sin DOM.
 */

// Navegadores incrustados de otras apps (redes sociales, mensajería): no ofrecen "Agregar a pantalla de inicio".
const NAVEGADOR_INCRUSTADO = /FBAN|FBAV|FB_IAB|Instagram|Line\/|Twitter|MicroMessenger|Snapchat|LinkedInApp/i;

/** Dispositivo iOS o iPadOS (este último se identifica como Mac con pantalla táctil). */
export const esIOS = ({ userAgent = '', platform = '', maxTouchPoints = 0 } = {}) => (
  /iPhone|iPad|iPod/i.test(userAgent) || (platform === 'MacIntel' && maxTouchPoints > 1)
);

/** iOS en un navegador común: donde la instalación es manual, desde el menú Compartir. */
export const esIOSConInstalacionManual = (entorno = {}) => (
  esIOS(entorno) && !NAVEGADOR_INCRUSTADO.test(entorno.userAgent ?? '')
);

/** La aplicación ya corre instalada: `display-mode: standalone` o, en iOS, `navigator.standalone`. */
export const estaInstalada = ({ modoStandalone = false, standaloneIOS = false } = {}) => (
  Boolean(modoStandalone) || standaloneIOS === true
);

export const MODO_BANNER_INSTALAR = 'instalar';
export const MODO_BANNER_IOS = 'ios';

/**
 * Qué muestra el banner: `instalar` cuando el navegador entregó el aviso de instalación (Chromium y Android),
 * `ios` con la indicación manual, o `null` si no corresponde (ya instalada, cerrado por el usuario o sin soporte).
 */
export const modoDelBanner = ({ instalada, cerrado, hayAviso, ios }) => {
  if (instalada || cerrado) return null;
  if (hayAviso) return MODO_BANNER_INSTALAR;
  return ios ? MODO_BANNER_IOS : null;
};
