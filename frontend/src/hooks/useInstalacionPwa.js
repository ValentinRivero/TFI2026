import { useCallback, useSyncExternalStore } from 'react';
import { PARAMETROS } from '../config/parametros.js';
import {
  esIOSConInstalacionManual, estaInstalada, modoDelBanner,
} from '../utils/pwa.js';

/**
 * Estado de la invitación a instalar la aplicación, compartido por todas las instancias de `Layout`. Vive en el
 * módulo y no en el componente porque el navegador emite `beforeinstallprompt` una sola vez: si la pantalla que lo
 * recibió se desmonta (por ejemplo, al pasar de una plantilla a otra), el aviso se perdería. Los oyentes se
 * registran al importar este módulo, que ocurre al arrancar la aplicación.
 */
const hayNavegador = typeof window !== 'undefined' && typeof navigator !== 'undefined';

const leerCierre = () => {
  try {
    return window.localStorage.getItem(PARAMETROS.pwa.claveBannerCerrado) === '1';
  } catch {
    return false;
  }
};

const guardarCierre = () => {
  try {
    window.localStorage.setItem(PARAMETROS.pwa.claveBannerCerrado, '1');
  } catch {
    // Sin almacenamiento disponible (modo privado, datos bloqueados): el aviso solo se oculta en esta sesión.
  }
};

const leerInstalada = () => {
  if (!hayNavegador) return false;
  return estaInstalada({
    modoStandalone: typeof window.matchMedia === 'function' && window.matchMedia('(display-mode: standalone)').matches,
    standaloneIOS: navigator.standalone,
  });
};

const ios = hayNavegador && esIOSConInstalacionManual({
  userAgent: navigator.userAgent,
  platform: navigator.platform,
  maxTouchPoints: navigator.maxTouchPoints,
});

let estado = Object.freeze({
  aviso: null,
  instalada: leerInstalada(),
  cerrado: hayNavegador ? leerCierre() : false,
});
const suscriptores = new Set();

const actualizar = (cambios) => {
  estado = Object.freeze({ ...estado, ...cambios });
  suscriptores.forEach((avisar) => avisar());
};

if (hayNavegador) {
  window.addEventListener('beforeinstallprompt', (evento) => {
    // Evita el mini aviso nativo: la invitación la muestra el banner de la aplicación.
    evento.preventDefault();
    actualizar({ aviso: evento });
  });
  window.addEventListener('appinstalled', () => actualizar({ aviso: null, instalada: true }));
  if (typeof window.matchMedia === 'function') {
    window.matchMedia('(display-mode: standalone)').addEventListener('change', () => {
      actualizar({ instalada: leerInstalada() });
    });
  }
}

const suscribir = (avisar) => {
  suscriptores.add(avisar);
  return () => suscriptores.delete(avisar);
};
const leerEstado = () => estado;

/**
 * Devuelve `{ modo, instalar, cerrar }`: `modo` es `'instalar'`, `'ios'` o `null` (ver `modoDelBanner`), `instalar`
 * dispara el aviso nativo del navegador y `cerrar` oculta el banner y recuerda la decisión en este dispositivo.
 */
export default function useInstalacionPwa() {
  const actual = useSyncExternalStore(suscribir, leerEstado, leerEstado);

  const cerrar = useCallback(() => {
    guardarCierre();
    actualizar({ cerrado: true });
  }, []);

  const instalar = useCallback(async () => {
    const { aviso } = estado;
    if (!aviso) return;
    // El aviso se puede usar una sola vez: se descarta aunque la persona lo rechace.
    actualizar({ aviso: null });
    try {
      await aviso.prompt();
      const { outcome } = await aviso.userChoice;
      if (outcome === 'dismissed') cerrar();
    } catch {
      // El navegador rechazó mostrar el aviso (por ejemplo, sin gesto del usuario): no hay nada que reintentar.
    }
  }, [cerrar]);

  const modo = modoDelBanner({
    instalada: actual.instalada,
    cerrado: actual.cerrado,
    hayAviso: actual.aviso !== null,
    ios,
  });

  return { modo, instalar, cerrar };
}
