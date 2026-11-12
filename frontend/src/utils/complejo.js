import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';

const { horasCancelacionMaximas, latitudMaxima, longitudMaxima } = PARAMETROS.panel;

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
});

const NUMERICOS = ['latitud', 'longitud', 'horas_limite_cancelacion'];

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
    if (campo === 'horas_limite_cancelacion') cuerpo[campo] = Number(valor);
    else cuerpo[campo] = valor.trim();
  });
  return cuerpo;
};

const fueraDeRango = (texto, limite) => texto.trim() === '' || !Number.isFinite(Number(texto)) || Math.abs(Number(texto)) > limite;

/** Errores por campo del formulario de configuración; un objeto vacío significa que se puede enviar. */
export const validarConfiguracion = (valores) => {
  const errores = {};
  if (valores.nombre.trim() === '') errores.nombre = t('configuracion.errorObligatorio');
  if (valores.direccion.trim() === '') errores.direccion = t('configuracion.errorObligatorio');
  if (fueraDeRango(valores.latitud, latitudMaxima)) errores.latitud = t('configuracion.errorLatitud', { maximo: latitudMaxima });
  if (fueraDeRango(valores.longitud, longitudMaxima)) errores.longitud = t('configuracion.errorLongitud', { maximo: longitudMaxima });
  const horas = valores.horas_limite_cancelacion.trim();
  if (horas === '' || !/^\d+$/.test(horas) || Number(horas) > horasCancelacionMaximas) {
    errores.horas_limite_cancelacion = t('configuracion.errorHoras', { maximo: horasCancelacionMaximas });
  }
  return errores;
};

/** Ids de servicios del borrador frente a los guardados: `true` si difieren (sin importar el orden). */
export const serviciosModificados = (guardados, elegidos) => (
  guardados.length !== elegidos.length || guardados.some((id) => !elegidos.includes(id))
);
