import { ES_DIA_COMPLETO, ES_FRANJA_HORARIA, VIGENCIA_EXCEPCION } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { parsearFecha } from './formatos.js';

export const FILTROS_EXCEPCIONES_INICIALES = Object.freeze({
  vigencia: VIGENCIA_EXCEPCION.VIGENTES,
  cancha: '',
  motivo: '',
  fecha: '',
});

/**
 * Parámetros de `GET /api/excepciones/` para el complejo, los filtros y la página. Un filtro vacío o una fecha que
 * no es de calendario no viaja: el backend responde 400 ante un valor inválido.
 */
export const aParametrosExcepciones = (complejoId, filtros, pagina) => {
  const params = { complejo: complejoId, page: pagina };
  if (filtros.vigencia) params.vigencia = filtros.vigencia;
  if (filtros.cancha) params.cancha = filtros.cancha;
  if (filtros.motivo) params.tipo_motivo = filtros.motivo;
  if (parsearFecha(filtros.fecha)) params.fecha = filtros.fecha;
  return params;
};

export const VALORES_EXCEPCION_INICIALES = Object.freeze({
  alcance: 'complejo',
  cancha: '',
  fecha_inicio: '',
  fecha_fin: '',
  es_dia_completo: String(ES_DIA_COMPLETO),
  hora_inicio: '',
  hora_fin: '',
  tipo_motivo: '',
  descripcion: '',
});

const esDiaCompleto = (valores) => Number(valores.es_dia_completo) === ES_DIA_COMPLETO;

/** Errores por campo del formulario de alta; `hoy` es `AAAA-MM-DD`. Un objeto vacío significa que se puede enviar. */
export const validarExcepcion = (valores, hoy) => {
  const errores = {};
  if (valores.alcance === 'cancha' && !valores.cancha) errores.cancha = t('excepciones.errorCancha');
  if (!parsearFecha(valores.fecha_inicio)) errores.fecha_inicio = t('excepciones.errorFecha');
  else if (valores.fecha_inicio < hoy) errores.fecha_inicio = t('excepciones.errorPasado');
  if (!parsearFecha(valores.fecha_fin)) errores.fecha_fin = t('excepciones.errorFecha');
  else if (!errores.fecha_inicio && valores.fecha_fin < valores.fecha_inicio) errores.fecha_fin = t('excepciones.errorFin');
  if (!valores.tipo_motivo) errores.tipo_motivo = t('excepciones.errorMotivo');
  if (!esDiaCompleto(valores)) {
    if (!valores.hora_inicio) errores.hora_inicio = t('excepciones.errorHora');
    if (!valores.hora_fin) errores.hora_fin = t('excepciones.errorHora');
    if (valores.hora_inicio && valores.hora_fin && valores.hora_fin <= valores.hora_inicio) {
      errores.hora_fin = t('excepciones.errorHoraFin');
    }
  }
  return errores;
};

/** Cuerpo del `POST /api/excepciones/`: sin horas en un día completo y sin cancha cuando afecta a todo el complejo. */
export const cuerpoExcepcion = (complejoId, valores) => {
  const completo = esDiaCompleto(valores);
  return {
    complejo: complejoId,
    cancha: valores.alcance === 'cancha' ? Number(valores.cancha) : null,
    fecha_inicio: valores.fecha_inicio,
    fecha_fin: valores.fecha_fin,
    es_dia_completo: completo ? ES_DIA_COMPLETO : ES_FRANJA_HORARIA,
    hora_inicio: completo ? null : valores.hora_inicio,
    hora_fin: completo ? null : valores.hora_fin,
    tipo_motivo: Number(valores.tipo_motivo),
    descripcion: valores.descripcion.trim(),
  };
};
