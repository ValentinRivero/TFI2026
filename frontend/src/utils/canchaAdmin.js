import { t } from '../i18n/index.js';

export const VALORES_CANCHA_INICIALES = Object.freeze({
  nombre: '',
  deporte: '',
  tipo_superficie: '1',
  cobertura: '1',
  iluminacion: '1',
  duracion_turno_min: '60',
  precio_base: '',
  estado: '1',
});

/** Valores del formulario (siempre texto) a partir de una cancha guardada. */
export const valoresDeCancha = (cancha) => ({
  nombre: cancha.nombre,
  deporte: String(cancha.deporte),
  tipo_superficie: String(cancha.tipo_superficie),
  cobertura: String(cancha.cobertura),
  iluminacion: String(cancha.iluminacion),
  duracion_turno_min: String(cancha.duracion_turno_min),
  precio_base: String(Number(cancha.precio_base)),
  estado: String(cancha.estado),
});

const CODIGOS = ['deporte', 'tipo_superficie', 'cobertura', 'iluminacion', 'duracion_turno_min', 'estado'];

// Espejo de `precio_base`: hasta 10 dígitos con 2 decimales (core/serializers.py).
const PRECIO = /^\d{1,8}(\.\d{1,2})?$/;

/** Errores por campo del formulario de cancha; un objeto vacío significa que se puede enviar. */
export const validarCancha = (valores) => {
  const errores = {};
  if (valores.nombre.trim() === '') errores.nombre = t('gestionCanchas.errorNombre');
  if (!valores.deporte) errores.deporte = t('gestionCanchas.errorDeporte');
  if (!PRECIO.test(valores.precio_base.trim())) errores.precio_base = t('gestionCanchas.errorPrecio');
  return errores;
};

/**
 * Cuerpo del alta (todos los campos, con el complejo) o de la edición (solo lo que cambió respecto de `original`).
 * La duración y el estado de una cancha con reservas futuras pueden pedir confirmación en el backend.
 */
export const cuerpoCancha = (valores, { complejoId, original = null } = {}) => {
  const completo = { nombre: valores.nombre.trim(), precio_base: valores.precio_base.trim() };
  CODIGOS.forEach((campo) => {
    completo[campo] = Number(valores[campo]);
  });

  if (!original) return { complejo: complejoId, ...completo };

  const cuerpo = {};
  Object.entries(completo).forEach(([campo, valor]) => {
    const previo = original[campo];
    const igual = campo === 'precio_base' ? Number(valor) === Number(previo) : valor === previo;
    if (!igual) cuerpo[campo] = valor;
  });
  return cuerpo;
};
