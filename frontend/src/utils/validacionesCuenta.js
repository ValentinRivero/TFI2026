import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';

const { limitesCampos, cuenta, password: reglasPassword } = PARAMETROS;

// Espejo de las reglas de Django (core/serializers.py y core/serializers_auth.py): el backend es quien las hace cumplir
// y este módulo solo da el aviso inmediato en el formulario.
const escapar = (texto) => texto.replace(/[\\^$.*+?()[\]{}|/-]/g, '\\$&');

const PATRON_NOMBRE = /^[\p{L} '’.-]+$/u;
const ATOMO_EMAIL = "[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+";
const ETIQUETA_DOMINIO = '[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?';
const PATRON_EMAIL = new RegExp(`^${ATOMO_EMAIL}(?:\\.${ATOMO_EMAIL})*@${ETIQUETA_DOMINIO}(?:\\.${ETIQUETA_DOMINIO})+$`);
const PATRON_PASSWORD = new RegExp(`^[A-Za-z0-9${escapar(cuenta.passwordSimbolos)}]+$`);
const PATRON_TELEFONO = new RegExp(`^\\+?[0-9\\s()-]{6,${limitesCampos.telefono}}$`);

const obligatorio = () => t('validacion.obligatorio');

/** Nombre de persona: solo letras de cualquier idioma, espacios, apóstrofes, guiones y puntos; empieza con una letra. */
export const validarNombre = (valor) => {
  const nombre = valor.normalize('NFC').trim().replace(/\s+/g, ' ');
  if (nombre === '') return obligatorio();
  const letras = [...nombre].filter((caracter) => /\p{L}/u.test(caracter)).length;
  const valido = letras >= cuenta.nombreLargoMinimo
    && nombre.length <= limitesCampos.nombre
    && /^\p{L}/u.test(nombre)
    && PATRON_NOMBRE.test(nombre);
  return valido ? null : t('validacion.nombre', { minimo: cuenta.nombreLargoMinimo, maximo: limitesCampos.nombre });
};

/** Correo con formato válido (sin emojis ni espacios), dominio con punto y largo entre el mínimo y el máximo. */
export const validarEmail = (valor) => {
  const email = valor.trim();
  if (email === '') return obligatorio();
  const valido = email.length >= cuenta.emailLargoMinimo && email.length <= limitesCampos.email && PATRON_EMAIL.test(email);
  return valido ? null : t('validacion.email');
};

/** Teléfono opcional: vacío es válido; si se completa, solo números, espacios, guiones, paréntesis y un + inicial. */
export const validarTelefono = (valor) => {
  const telefono = valor.trim();
  return telefono === '' || PATRON_TELEFONO.test(telefono) ? null : t('validacion.telefono');
};

/** Contraseña nueva: letras ASCII, números y los símbolos permitidos, entre el largo mínimo y el máximo. */
export const validarPassword = (valor) => {
  if (valor === '') return obligatorio();
  if (!PATRON_PASSWORD.test(valor)) return t('validacion.passwordCaracteres', { simbolos: cuenta.passwordSimbolos });
  if (valor.length < reglasPassword.largoMinimo || valor.length > limitesCampos.password) {
    return t('validacion.passwordLargo', { minimo: reglasPassword.largoMinimo, maximo: limitesCampos.password });
  }
  return null;
};

const sinValidos = (errores) => Object.fromEntries(Object.entries(errores).filter(([, mensaje]) => mensaje !== null));

/** Errores por campo del formulario de registro (`{}` si todo es válido). */
export const validarRegistro = (valores) => sinValidos({
  nombre_completo: validarNombre(valores.nombre_completo),
  email: validarEmail(valores.email),
  telefono: validarTelefono(valores.telefono),
  password: validarPassword(valores.password),
});

/**
 * Errores por campo del inicio de sesión. La contraseña solo se controla vacía o demasiado larga: las reglas de
 * caracteres rigen al elegirla y no deben dejar afuera a una cuenta creada antes.
 */
export const validarLogin = (valores) => {
  let password = null;
  if (valores.password === '') password = obligatorio();
  else if (valores.password.length > limitesCampos.password) {
    password = t('validacion.passwordLargo', { minimo: reglasPassword.largoMinimo, maximo: limitesCampos.password });
  }
  return sinValidos({ email: validarEmail(valores.email), password });
};
