import { t } from '../i18n/index.js';
import { aFechaIso, parsearFecha } from './formatos.js';

export const FILTROS_TURNOS_FIJOS_INICIALES = Object.freeze({ cancha: '', estado: '', dia: '' });

/** Parámetros de `GET /api/turnos-fijos/` para el complejo, los filtros y la página. */
export const aParametrosTurnosFijos = (complejoId, filtros, pagina) => {
  const params = { complejo: complejoId, page: pagina };
  if (filtros.cancha) params.cancha = filtros.cancha;
  if (filtros.estado) params.estado = filtros.estado;
  if (filtros.dia !== '') params.dia_semana = filtros.dia;
  return params;
};

/** Parámetros de la bandeja de turnos fijos con fechas en espera por una excepción. */
export const aParametrosEnEspera = (complejoId, pagina) => ({ complejo: complejoId, en_espera: true, page: pagina });

export const VALORES_TURNO_FIJO_INICIALES = Object.freeze({
  cancha: '',
  dia_semana: '',
  hora_inicio: '',
  fecha_inicio_vigencia: '',
  fecha_fin_vigencia: '',
  nombre_cliente_manual: '',
  telefono_cliente_manual: '',
});

/** Errores por campo del alta de un turno fijo; `hoy` es `AAAA-MM-DD`. */
export const validarTurnoFijo = (valores, hoy) => {
  const errores = {};
  if (!valores.cancha) errores.cancha = t('turnosFijos.errorCancha');
  if (valores.dia_semana === '') errores.dia_semana = t('turnosFijos.errorDia');
  if (!valores.hora_inicio) errores.hora_inicio = t('turnosFijos.errorHora');
  if (!parsearFecha(valores.fecha_inicio_vigencia)) errores.fecha_inicio_vigencia = t('turnosFijos.errorFecha');
  else if (valores.fecha_inicio_vigencia < hoy) errores.fecha_inicio_vigencia = t('turnosFijos.errorPasado');
  if (valores.fecha_fin_vigencia) {
    if (!parsearFecha(valores.fecha_fin_vigencia)) errores.fecha_fin_vigencia = t('turnosFijos.errorFecha');
    else if (!errores.fecha_inicio_vigencia && valores.fecha_fin_vigencia < valores.fecha_inicio_vigencia) {
      errores.fecha_fin_vigencia = t('turnosFijos.errorFin');
    }
  }
  if (valores.nombre_cliente_manual.trim() === '') errores.nombre_cliente_manual = t('turnosFijos.errorNombre');
  return errores;
};

/** Cuerpo del `POST /api/turnos-fijos/`; sin fecha de fin el turno rige por tiempo indefinido. */
export const cuerpoTurnoFijo = (valores) => ({
  cancha: Number(valores.cancha),
  dia_semana: Number(valores.dia_semana),
  hora_inicio: valores.hora_inicio,
  fecha_inicio_vigencia: valores.fecha_inicio_vigencia,
  fecha_fin_vigencia: valores.fecha_fin_vigencia || null,
  nombre_cliente_manual: valores.nombre_cliente_manual.trim(),
  telefono_cliente_manual: valores.telefono_cliente_manual.trim(),
});

/**
 * Próximas fechas de un turno fijo que se pueden llevar a la agenda: las que caen en su día de la semana (0 lunes a
 * 6 domingo), desde hoy o desde el inicio de la vigencia (lo que sea posterior) y hasta el fin de la vigencia.
 */
export const proximasFechasDeTurnoFijo = (turno, hoy, cantidad) => {
  const desde = turno.fecha_inicio_vigencia > hoy ? turno.fecha_inicio_vigencia : hoy;
  const cursor = parsearFecha(desde);
  if (!cursor) return [];
  const fechas = [];
  const ultimaFecha = turno.fecha_fin_vigencia ?? null;
  // Un turno fijo sin fin no corta el recorrido: lo acota la cantidad pedida.
  while (fechas.length < cantidad) {
    const iso = aFechaIso(cursor);
    if (ultimaFecha && iso > ultimaFecha) break;
    if ((cursor.getDay() + 6) % 7 === turno.dia_semana) {
      fechas.push(iso);
      cursor.setDate(cursor.getDate() + 7);
    } else {
      cursor.setDate(cursor.getDate() + 1);
    }
  }
  return fechas;
};

/** Una fila por cada fecha en espera de cada turno fijo, para la bandeja de resolución. */
export const aFilasEnEspera = (turnos) => (
  turnos.flatMap((turno) => (turno.fechas_en_espera ?? []).map((espera) => ({
    clave: `${turno.id}:${espera.fecha}`,
    turno,
    fecha: espera.fecha,
    motivo: espera.motivo,
  })))
);

const aMinutos = (hora) => {
  const partes = /^(\d{1,2}):(\d{2})/.exec(hora ?? '');
  return partes ? Number(partes[1]) * 60 + Number(partes[2]) : null;
};

const dosDigitos = (numero) => String(numero).padStart(2, '0');
const aHora = (minutos) => `${dosDigitos(Math.floor(minutos / 60))}:${dosDigitos(minutos % 60)}`;

/**
 * Bloques horarios válidos de una cancha en un día de la semana (0 lunes a 6 domingo), igual que los arma la grilla:
 * cada rango de apertura genera sus turnos por separado, uno tras otro desde la apertura, de `duracionMin` minutos, y
 * un resto menor a un turno completo no se ofrece. Devuelve `[{ hora_inicio, hora_fin, precio }]` ordenado por hora,
 * con el precio diferenciado del rango o, si no tiene, `precioBase`.
 */
export const bloquesDeHorarios = (rangos, diaSemana, duracionMin, precioBase = null) => {
  const duracion = Number(duracionMin);
  if (!Number.isInteger(duracion) || duracion <= 0) return [];
  const bloques = [];
  (rangos ?? []).filter((rango) => Number(rango.dia_semana) === Number(diaSemana)).forEach((rango) => {
    const apertura = aMinutos(rango.hora_apertura);
    const cierre = aMinutos(rango.hora_cierre);
    if (apertura === null || cierre === null) return;
    for (let inicio = apertura; inicio + duracion <= cierre; inicio += duracion) {
      bloques.push({
        hora_inicio: aHora(inicio),
        hora_fin: aHora(inicio + duracion),
        precio: rango.precio_diferenciado ?? precioBase,
      });
    }
  });
  return bloques.sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
};
