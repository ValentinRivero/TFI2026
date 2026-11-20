import { PARAMETROS } from '../config/parametros.js';

/**
 * Tema claro u oscuro de la interfaz. Son funciones puras: reciben el almacenamiento, la consulta de medios y el
 * documento en lugar de leerlos del navegador, así se prueban sin DOM. Los valores coinciden con los de
 * `data-bs-theme` de Bootstrap 5.3.
 */
export const TEMA_CLARO = 'light';
export const TEMA_OSCURO = 'dark';

const { claveAlmacenamiento, consultaOscuro, colorBarra } = PARAMETROS.tema;

export const esTemaValido = (valor) => valor === TEMA_CLARO || valor === TEMA_OSCURO;

const almacenamientoDelNavegador = () => window.localStorage;
const consultarMedios = (consulta) => window.matchMedia(consulta);

/** Elección guardada en este dispositivo, o `null` si no hay, está corrupta o el almacenamiento no es accesible. */
export const leerTemaGuardado = (obtenerAlmacen = almacenamientoDelNavegador) => {
  try {
    const valor = obtenerAlmacen().getItem(claveAlmacenamiento);
    return esTemaValido(valor) ? valor : null;
  } catch {
    return null;
  }
};

/** Guarda la elección manual. Devuelve `false` si el tema no es válido o el almacenamiento falla (modo privado). */
export const guardarTema = (tema, obtenerAlmacen = almacenamientoDelNavegador) => {
  if (!esTemaValido(tema)) return false;
  try {
    obtenerAlmacen().setItem(claveAlmacenamiento, tema);
    return true;
  } catch {
    return false;
  }
};

/** Preferencia del sistema operativo; sin soporte de `matchMedia` se asume el modo claro. */
export const temaDelSistema = (consultar = consultarMedios) => {
  try {
    return consultar(consultaOscuro).matches ? TEMA_OSCURO : TEMA_CLARO;
  } catch {
    return TEMA_CLARO;
  }
};

/** La elección guardada manda; sin ella rige la preferencia del sistema y, en último caso, el modo claro. */
export const resolverTema = ({ guardado, sistema } = {}) => {
  if (esTemaValido(guardado)) return guardado;
  return esTemaValido(sistema) ? sistema : TEMA_CLARO;
};

export const alternarTema = (tema) => (tema === TEMA_OSCURO ? TEMA_CLARO : TEMA_OSCURO);

export const colorBarraDe = (tema) => colorBarra[tema] ?? colorBarra[TEMA_CLARO];

/** Aplica el tema al documento: atributo de Bootstrap y color de la barra del navegador o de la PWA instalada. */
export const aplicarTema = (tema, documento = document) => {
  if (!esTemaValido(tema)) return;
  documento.documentElement.setAttribute('data-bs-theme', tema);
  documento.querySelector('meta[name="theme-color"]')?.setAttribute('content', colorBarraDe(tema));
};
