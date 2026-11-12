import { t } from '../i18n/index.js';

/**
 * Error uniforme de ambos backends:
 * - `status`: código HTTP, o `0` si no hubo respuesta (red caída o tiempo agotado).
 * - `mensaje`: texto general en español, listo para mostrar.
 * - `campos`: errores por campo (`{ email: 'Ya existe una cuenta con ese email.' }`).
 * - `extra`: el resto del cuerpo (`conflictos`, `requiere_confirmacion`...), que las confirmaciones de 6.2 y 6.3 necesitan.
 */
export class ErrorApi extends Error {
  constructor({ status = 0, mensaje, campos = {}, extra = {}, tiempoAgotado = false }) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.status = status;
    this.mensaje = mensaje;
    this.campos = campos;
    this.extra = extra;
    this.tiempoAgotado = tiempoAgotado;
  }

  get sinRespuesta() {
    return this.status === 0;
  }
}

const esObjeto = (valor) => valor !== null && typeof valor === 'object' && !Array.isArray(valor);
const esTexto = (valor) => typeof valor === 'string' && valor.trim() !== '';

const unirTextos = (lista) => lista.filter(esTexto).join(' ');

// Django responde `detail` como un objeto por campo, con listas de mensajes y, a veces, objetos anidados.
const aplanar = (objeto, prefijo, salida) => {
  Object.entries(objeto).forEach(([clave, valor]) => {
    const ruta = prefijo ? `${prefijo}.${clave}` : clave;
    if (esTexto(valor)) {
      salida[ruta] = valor;
    } else if (Array.isArray(valor)) {
      const texto = unirTextos(valor);
      if (texto) salida[ruta] = texto;
      valor.forEach((item, indice) => {
        if (esObjeto(item)) aplanar(item, `${ruta}.${indice}`, salida);
      });
    } else if (esObjeto(valor)) {
      aplanar(valor, ruta, salida);
    }
  });
};

const CLAVES_GENERALES = ['non_field_errors', '__all__'];

const mensajePorEstado = (status) => {
  if (status === 0) return t('errores.red');
  if (status === 400) return t('errores.datosInvalidos');
  if (status === 401) return t('errores.noAutenticado');
  if (status === 403) return t('errores.sinPermiso');
  if (status === 404) return t('errores.noEncontrado');
  if (status === 409) return t('errores.conflicto');
  if (status === 429) return t('errores.demasiadasSolicitudes');
  if (status >= 500) return t('errores.servicio');
  return t('errores.generico');
};

// El texto del backend (ya en español) se muestra salvo en los errores de límite o de servicio, donde su contenido
// puede ser técnico: ahí se usa el mensaje general.
const usaMensajeGeneral = (status) => status === 0 || status === 429 || status >= 500;

/**
 * Estructura uniforme a partir de una respuesta HTTP de error de Django (`{ error, detail }`) o de Node
 * (`{ error, mensaje, detalles }`). Un cuerpo que no es JSON de la API (por ejemplo, una página de error del proxy)
 * da el mensaje general del código.
 */
export const normalizarRespuesta = (status, cuerpo) => {
  const { error: _marca, detail, mensaje, detalles, ...extra } = esObjeto(cuerpo) ? cuerpo : {};
  const campos = {};
  let general = null;

  if (esTexto(detail)) {
    general = detail;
  } else if (Array.isArray(detail)) {
    general = unirTextos(detail) || null;
  } else if (esObjeto(detail)) {
    aplanar(detail, '', campos);
    general = CLAVES_GENERALES.map((clave) => campos[clave]).find(Boolean) ?? null;
    CLAVES_GENERALES.forEach((clave) => delete campos[clave]);
  }

  if (esTexto(mensaje)) general ??= mensaje;
  if (Array.isArray(detalles)) {
    detalles.forEach((detalleDeCampo) => {
      if (esObjeto(detalleDeCampo) && esTexto(detalleDeCampo.campo) && esTexto(detalleDeCampo.mensaje)) {
        campos[detalleDeCampo.campo] ??= detalleDeCampo.mensaje;
      }
    });
  }

  return new ErrorApi({
    status,
    mensaje: general && !usaMensajeGeneral(status) ? general : mensajePorEstado(status),
    campos,
    extra,
  });
};

/** Error de un pedido de Axios (con o sin respuesta) como `ErrorApi`. Uno que ya es `ErrorApi` se devuelve igual. */
export const normalizarError = (error) => {
  if (error instanceof ErrorApi) return error;
  if (error?.response) return normalizarRespuesta(error.response.status, error.response.data);
  const tiempoAgotado = error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT';
  return new ErrorApi({
    status: 0,
    mensaje: tiempoAgotado ? t('errores.tiempo') : t('errores.red'),
    tiempoAgotado,
  });
};
