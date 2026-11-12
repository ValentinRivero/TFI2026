import { PARAMETROS } from '../config/parametros.js';
import es from './es.js';

// Para sumar un idioma alcanza con registrar su diccionario acá y cambiar `idioma` en parametros.js.
const DICCIONARIOS = { es };

const buscar = (diccionario, clave) => clave.split('.').reduce(
  (nodo, parte) => (nodo !== null && typeof nodo === 'object' ? nodo[parte] : undefined),
  diccionario,
);

/**
 * Texto de la interfaz por clave con puntos (`comun.cargando`). Reemplaza cada `%variable%` por su valor en
 * `params`; un marcador sin valor queda intacto. Una clave inexistente devuelve la clave.
 * El resultado es texto plano: se muestra con JSX normal, nunca como HTML.
 */
export const t = (clave, params = {}, idioma = PARAMETROS.idioma) => {
  const texto = buscar(DICCIONARIOS[idioma] ?? DICCIONARIOS.es, clave);
  if (typeof texto !== 'string') {
    if (import.meta.env?.DEV) console.warn(`Falta la clave de texto: ${clave}`);
    return clave;
  }
  return texto.replace(/%(\w+)%/g, (marcador, nombre) => (
    Object.hasOwn(params, nombre) ? String(params[nombre]) : marcador
  ));
};
