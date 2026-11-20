import { useSyncExternalStore } from 'react';
import { PARAMETROS } from '../config/parametros.js';
import {
  alternarTema,
  aplicarTema,
  guardarTema,
  leerTemaGuardado,
  resolverTema,
  TEMA_CLARO,
  TEMA_OSCURO,
  temaDelSistema,
} from '../utils/tema.js';

// El tema es único para toda la aplicación: vive acá y no en cada botón, así todos los que lo muestran quedan sincronizados.
let temaActual = null;
const oyentes = new Set();

const resolverInicial = () => resolverTema({ guardado: leerTemaGuardado(), sistema: temaDelSistema() });

const obtenerTema = () => {
  if (temaActual === null) {
    temaActual = resolverInicial();
    aplicarTema(temaActual);
  }
  return temaActual;
};

const fijarTema = (tema) => {
  if (tema === temaActual) return;
  temaActual = tema;
  aplicarTema(tema);
  oyentes.forEach((oyente) => oyente());
};

// Mientras no haya elección manual, el tema sigue a la preferencia del sistema en tiempo real; la elección guardada
// también se sincroniza entre pestañas del mismo dispositivo.
const escucharCambios = () => {
  let consulta = null;
  try {
    consulta = window.matchMedia(PARAMETROS.tema.consultaOscuro);
  } catch {
    consulta = null;
  }
  const alCambiarSistema = () => {
    if (leerTemaGuardado() === null) fijarTema(temaDelSistema());
  };
  const alCambiarAlmacenamiento = (evento) => {
    if (evento.key === PARAMETROS.tema.claveAlmacenamiento || evento.key === null) fijarTema(resolverInicial());
  };
  consulta?.addEventListener('change', alCambiarSistema);
  window.addEventListener('storage', alCambiarAlmacenamiento);
  return () => {
    consulta?.removeEventListener('change', alCambiarSistema);
    window.removeEventListener('storage', alCambiarAlmacenamiento);
  };
};

let dejarDeEscuchar = null;

const suscribir = (oyente) => {
  oyentes.add(oyente);
  if (oyentes.size === 1) dejarDeEscuchar = escucharCambios();
  return () => {
    oyentes.delete(oyente);
    if (oyentes.size === 0) {
      dejarDeEscuchar?.();
      dejarDeEscuchar = null;
    }
  };
};

const alternar = () => {
  const siguiente = alternarTema(obtenerTema());
  guardarTema(siguiente);
  fijarTema(siguiente);
};

/**
 * Tema activo (`light` o `dark`) y la acción para alternarlo. Sin elección guardada sigue la preferencia del
 * sistema; la primera vez que la persona alterna, su elección se guarda en el dispositivo (solo el nombre del tema,
 * nunca datos personales) y deja de seguir al sistema.
 */
export default function useTema() {
  const tema = useSyncExternalStore(suscribir, obtenerTema, () => TEMA_CLARO);
  return { tema, esOscuro: tema === TEMA_OSCURO, alternar };
}
