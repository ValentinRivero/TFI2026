import { RUTAS_PANEL } from '../config/catalogos.js';
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
    rutaPanel: RUTAS_PANEL.canchas,
  }),
  servicios: Object.freeze({
    ruta: '/api/sistema/servicios/',
    largoMaximo: limitesCampos.nombreServicio,
    textos: 'catalogoSistema.servicios',
    rutaPanel: RUTAS_PANEL.configuracion,
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

export const FILTROS_CATALOGO_INICIALES = Object.freeze({ busqueda: '', estado: '' });

/** Texto sin mayúsculas ni tildes, para buscar sin distinguirlas ("Pádel" coincide con "padel"). */
export const normalizarParaBuscar = (texto) => (
  String(texto ?? '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim()
);

export const hayFiltroActivo = (filtros) => normalizarParaBuscar(filtros.busqueda) !== '' || filtros.estado !== '';

/**
 * Registros que cumplen la búsqueda (todas las palabras escritas aparecen en alguno de los textos del registro) y el
 * estado elegido (`''` no filtra). `textosDe(registro)` devuelve los textos donde se busca. Función pura: no modifica la lista.
 */
export const filtrarCatalogo = (items, filtros, textosDe = (item) => [item.nombre]) => {
  const palabras = normalizarParaBuscar(filtros.busqueda).split(/\s+/).filter(Boolean);
  return items.filter((item) => {
    if (filtros.estado !== '' && String(item.estado) !== filtros.estado) return false;
    if (palabras.length === 0) return true;
    const texto = textosDe(item).map(normalizarParaBuscar).join(' ');
    return palabras.every((palabra) => texto.includes(palabra));
  });
};
