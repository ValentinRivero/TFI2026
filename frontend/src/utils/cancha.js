import { COBERTURA, DURACION_TURNO, ILUMINACION, TIPO_SUPERFICIE } from '../config/catalogos.js';
import { t } from '../i18n/index.js';

// El catálogo de códigos manda; si el backend suma un valor que el cliente todavía no conoce, se usa su nombre.
const etiquetaDe = (catalogo, codigo, nombreApi) => catalogo[codigo]?.etiqueta ?? nombreApi ?? '';

/** Superficie, cobertura, iluminación y duración del turno de una cancha, ya como texto para mostrar. */
export const describirCancha = (cancha) => ({
  superficie: etiquetaDe(TIPO_SUPERFICIE, cancha.tipo_superficie, cancha.tipo_superficie_nombre),
  cobertura: etiquetaDe(COBERTURA, cancha.cobertura, cancha.cobertura_nombre),
  iluminacion: etiquetaDe(ILUMINACION, cancha.iluminacion, cancha.iluminacion_nombre),
  duracion: DURACION_TURNO[cancha.duracion_turno_min]?.etiqueta ?? t('cancha.minutos', { minutos: cancha.duracion_turno_min }),
});
