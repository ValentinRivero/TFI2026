import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { normalizarAlias, normalizarCbu, validarSena } from './pagos.js';

const { horasCancelacionMaximas, latitudMaxima, longitudMaxima, coordenadasDecimales } = PARAMETROS.panel;

/**
 * Complejo activo del panel: el elegido si sigue en la lista; si no (primera carga, complejo dado de baja, cambio de
 * cuenta), el primero. Con la lista vacía no hay complejo activo.
 */
export const resolverComplejoActivo = (complejos, idElegido) => (
  complejos.find((complejo) => complejo.id === idElegido) ?? complejos[0] ?? null
);

const aTexto = (valor) => (valor === null || valor === undefined ? '' : String(valor));

/** Valores de los campos del formulario de configuración (siempre texto, como los entrega un `<input>`). */
export const valoresDeComplejo = (complejo) => ({
  nombre: aTexto(complejo.nombre),
  direccion: aTexto(complejo.direccion),
  latitud: aTexto(complejo.latitud),
  longitud: aTexto(complejo.longitud),
  telefono_contacto: aTexto(complejo.telefono_contacto),
  horas_limite_cancelacion: aTexto(complejo.horas_limite_cancelacion),
  info_sena: aTexto(complejo.info_sena),
  porcentaje_sena: aTexto(complejo.porcentaje_sena ?? 0),
  alias_transferencia: aTexto(complejo.alias_transferencia),
  titular_transferencia: aTexto(complejo.titular_transferencia),
  cbu_cvu_transferencia: aTexto(complejo.cbu_cvu_transferencia),
});

const NUMERICOS = ['latitud', 'longitud', 'horas_limite_cancelacion', 'porcentaje_sena'];
const ENTEROS = ['horas_limite_cancelacion', 'porcentaje_sena'];

const cambio = (campo, valor, original) => (
  NUMERICOS.includes(campo)
    ? valor.trim() !== '' && Number(valor) !== Number(original)
    : valor.trim() !== aTexto(original).trim()
);

/**
 * Cuerpo del `PATCH` con solo los campos que cambiaron respecto del complejo guardado. Los números viajan como
 * texto decimal (latitud y longitud) o entero (horas) tal como los espera la API.
 */
export const cuerpoConfiguracion = (valores, complejo) => {
  const cuerpo = {};
  Object.entries(valores).forEach(([campo, valor]) => {
    if (!cambio(campo, valor, complejo[campo])) return;
    if (ENTEROS.includes(campo)) cuerpo[campo] = Number(valor);
    else if (campo === 'alias_transferencia') cuerpo[campo] = normalizarAlias(valor);
    else if (campo === 'cbu_cvu_transferencia') cuerpo[campo] = normalizarCbu(valor);
    else cuerpo[campo] = valor.trim();
  });
  return cuerpo;
};

const fueraDeRango = (texto, limite) => texto.trim() === '' || !Number.isFinite(Number(texto)) || Math.abs(Number(texto)) > limite;

const conDemasiadosDecimales = (texto) => (texto.trim().split('.')[1]?.length ?? 0) > coordenadasDecimales;

/** Error de una coordenada (rango o cantidad de decimales que admite la base), o `undefined` si es válida. */
const errorDeCoordenada = (texto, limite, claveRango) => {
  if (fueraDeRango(texto, limite)) return t(claveRango, { maximo: limite });
  if (conDemasiadosDecimales(texto)) return t('configuracion.errorDecimales', { decimales: coordenadasDecimales });
  return undefined;
};

/** Errores por campo del formulario de configuración; un objeto vacío significa que se puede enviar. */
export const validarConfiguracion = (valores) => {
  const errores = {};
  if (valores.nombre.trim() === '') errores.nombre = t('configuracion.errorObligatorio');
  if (valores.direccion.trim() === '') errores.direccion = t('configuracion.errorObligatorio');
  const errorLatitud = errorDeCoordenada(valores.latitud, latitudMaxima, 'configuracion.errorLatitud');
  if (errorLatitud) errores.latitud = errorLatitud;
  const errorLongitud = errorDeCoordenada(valores.longitud, longitudMaxima, 'configuracion.errorLongitud');
  if (errorLongitud) errores.longitud = errorLongitud;
  const horas = valores.horas_limite_cancelacion.trim();
  if (horas === '' || !/^\d+$/.test(horas) || Number(horas) > horasCancelacionMaximas) {
    errores.horas_limite_cancelacion = t('configuracion.errorHoras', { maximo: horasCancelacionMaximas });
  }
  return errores;
};

/**
 * Validación de la configuración del complejo: la de los datos comerciales más la de la seña y la transferencia.
 * El alta de un complejo nuevo (superadmin) no lleva seña y usa solo `validarConfiguracion`.
 */
export const validarConfiguracionConSena = (valores) => ({ ...validarConfiguracion(valores), ...validarSena(valores) });

/** Ids de servicios del borrador frente a los guardados: `true` si difieren (sin importar el orden). */
export const serviciosModificados = (guardados, elegidos) => (
  guardados.length !== elegidos.length || guardados.some((id) => !elegidos.includes(id))
);
