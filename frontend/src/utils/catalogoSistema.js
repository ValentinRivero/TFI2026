import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';

const { limitesCampos, cuenta } = PARAMETROS;

/**
 * Catálogos maestros que administra el superadmin con la misma pantalla: la ruta de la API, el largo máximo del nombre
 * (espejo de `core/models.py`) y el grupo de textos de la interfaz (`catalogoSistema.<grupo>` en `i18n/es.js`).
 */
export const CATALOGOS_SISTEMA = Object.freeze({
  deportes: Object.freeze({
    ruta: '/api/sistema/deportes/',
    largoMaximo: limitesCampos.nombreDeporte,
    textos: 'catalogoSistema.deportes',
  }),
  servicios: Object.freeze({
    ruta: '/api/sistema/servicios/',
    largoMaximo: limitesCampos.nombreServicio,
    textos: 'catalogoSistema.servicios',
  }),
});

/** Nombre sin espacios en los extremos y con espacios internos simples, como lo guarda el backend. */
export const normalizarNombre = (texto) => (texto ?? '').trim().replace(/\s+/g, ' ');

/** Error del nombre de un ítem del catálogo (obligatorio, entre el mínimo y el máximo del catálogo) o `undefined`. */
export const validarNombreCatalogo = (nombre, recurso) => {
  const limpio = normalizarNombre(nombre);
  const { largoMaximo } = CATALOGOS_SISTEMA[recurso];
  if (limpio === '') return t('catalogoSistema.errorNombreVacio');
  if (limpio.length < cuenta.nombreLargoMinimo) {
    return t('catalogoSistema.errorNombreCorto', { minimo: cuenta.nombreLargoMinimo });
  }
  if (limpio.length > largoMaximo) return t('catalogoSistema.errorNombreLargo', { maximo: largoMaximo });
  return undefined;
};

/** Texto de la cantidad de usos de un ítem (`1 cancha`, `3 canchas`) con el grupo de textos de su catálogo. */
export const textoDeUsos = (recurso, usos) => (
  t(`${CATALOGOS_SISTEMA[recurso].textos}.${usos === 1 ? 'usosUno' : 'usosVarios'}`, { cantidad: usos })
);
