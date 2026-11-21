import {
  ESTADOS_QUE_EXIGEN_TURNO_INICIADO,
  ESTADOS_REAPERTURA,
  ESTADOS_RESERVA_CANCELABLES,
  ESTADOS_RESERVA_CANCELADOS,
  PERIODOS_AGENDA,
  RESERVA_SENADA,
  SENTIDO_PERIODO,
  TRANSICIONES_AGENDA,
  VISTA_AGENDA,
} from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { diasEntre, parsearFecha, sumarDias } from './formatos.js';
import { tieneSena } from './pagos.js';
import { instanteDelTurno } from './reservas.js';

/** Vista de la agenda que pide la ruta (`?vista=`); un valor desconocido o ausente abre las reservas del día. */
export const vistaDeAgenda = (valor) => (
  Object.values(VISTA_AGENDA).includes(valor) ? valor : VISTA_AGENDA.RESERVAS
);

/**
 * La agenda abre en el día de hoy; sin fecha lista todas las reservas del complejo. Con `conRango` la consulta usa
 * `fecha_desde` y `fecha_hasta` (ambas incluidas) en lugar de `fecha`; el rango arranca en hoy.
 */
export const filtrosAgendaIniciales = (hoy) => ({
  fecha: hoy,
  conRango: false,
  fecha_desde: hoy,
  fecha_hasta: hoy,
  cancha: '',
  estado: '',
  conConflicto: false,
});

/** Errores por campo del rango de fechas; sin rango activo no hay nada que validar. `{}` significa que se puede consultar. */
export const validarFiltrosAgenda = (filtros) => {
  if (!filtros.conRango) return {};
  const errores = {};
  if (!parsearFecha(filtros.fecha_desde)) errores.fecha_desde = t('agenda.errorFecha');
  if (!parsearFecha(filtros.fecha_hasta)) errores.fecha_hasta = t('agenda.errorFecha');
  if (!errores.fecha_desde && !errores.fecha_hasta && diasEntre(filtros.fecha_desde, filtros.fecha_hasta) < 0) {
    errores.fecha_hasta = t('agenda.errorOrdenRango');
  }
  return errores;
};

/**
 * Cambios de filtros al activar o desactivar el rango. Al activarlo parte del día que se estaba viendo (hoy, si no había
 * uno válido); al desactivarlo vuelve al día único con la fecha inicial del rango.
 */
export const cambiosAlAlternarRango = (filtros, activo, hoy) => {
  if (activo) {
    const base = parsearFecha(filtros.fecha) ? filtros.fecha : hoy;
    return { conRango: true, fecha_desde: base, fecha_hasta: base };
  }
  return { conRango: false, fecha: parsearFecha(filtros.fecha_desde) ? filtros.fecha_desde : hoy };
};

/**
 * Rango `{ fecha_desde, fecha_hasta }` de un período rápido, o `null` si no existe. Los pasados (`semana`, `mes` y
 * `trimestre`) terminan hoy; los futuros (`proxima-semana`, `proximo-mes` y `proximo-trimestre`) empiezan hoy. En
 * ambos, hoy queda incluido y la cantidad de días es la del período.
 */
export const rangoDelPeriodo = (valor, hoy) => {
  const periodo = PERIODOS_AGENDA.find((candidato) => candidato.valor === valor);
  if (!periodo) return null;
  const extremo = sumarDias(hoy, periodo.sentido === SENTIDO_PERIODO.FUTURO ? periodo.dias - 1 : -(periodo.dias - 1));
  return periodo.sentido === SENTIDO_PERIODO.FUTURO
    ? { fecha_desde: hoy, fecha_hasta: extremo }
    : { fecha_desde: extremo, fecha_hasta: hoy };
};

/** Período rápido que coincide con el rango de los filtros (para marcarlo en el desplegable), o `''` si es un rango a mano. */
export const periodoActivo = (filtros, hoy) => {
  if (!filtros.conRango) return '';
  const coincide = PERIODOS_AGENDA.find(({ valor }) => {
    const rango = rangoDelPeriodo(valor, hoy);
    return rango.fecha_desde === filtros.fecha_desde && rango.fecha_hasta === filtros.fecha_hasta;
  });
  return coincide?.valor ?? '';
};

/** Día con el que arranca el alta manual: el que se ve en la agenda o, con rango, su inicio. Una fecha pasada o inválida cae a hoy. */
export const fechaInicialDeAlta = (filtros, hoy) => {
  const elegida = filtros.conRango ? filtros.fecha_desde : filtros.fecha;
  if (!parsearFecha(elegida)) return hoy;
  return filtros.conRango && elegida < hoy ? hoy : elegida;
};

/**
 * Parámetros de `GET /api/agenda/` para el complejo, los filtros y la página. Un filtro vacío o una fecha que no es
 * de calendario no viaja: el backend responde 400 ante un valor inválido.
 */
export const aParametrosAgenda = (complejoId, filtros, pagina) => {
  const params = { complejo: complejoId, page: pagina };
  if (filtros.conRango) {
    if (parsearFecha(filtros.fecha_desde)) params.fecha_desde = filtros.fecha_desde;
    if (parsearFecha(filtros.fecha_hasta)) params.fecha_hasta = filtros.fecha_hasta;
  } else if (parsearFecha(filtros.fecha)) {
    params.fecha = filtros.fecha;
  }
  if (filtros.cancha) params.cancha = filtros.cancha;
  if (filtros.estado) params.estado = filtros.estado;
  if (filtros.conConflicto) params.con_conflicto = true;
  return params;
};

const yaComenzo = (reserva, ahora) => {
  const inicio = instanteDelTurno(reserva.fecha_turno, reserva.hora_inicio);
  return Boolean(inicio) && inicio <= ahora;
};

/**
 * Estados a los que se puede pasar una reserva desde la agenda: las transiciones del backend, sin ausente ni
 * completada mientras el turno no empezó, y sin «Señada» si la reserva no tiene seña acordada. El servidor valida
 * igual: esto solo decide qué se ofrece.
 */
export const estadosSiguientes = (reserva, ahora = new Date()) => (
  (TRANSICIONES_AGENDA[reserva.estado] ?? []).filter(
    (estado) => (!ESTADOS_QUE_EXIGEN_TURNO_INICIADO.includes(estado) || yaComenzo(reserva, ahora))
      && (estado !== RESERVA_SENADA || tieneSena(reserva)),
  )
);

/** Estados con los que se puede reabrir una reserva cancelada; «Señada» solo si tiene seña acordada. */
export const estadosDeReapertura = (reserva) => (
  ESTADOS_REAPERTURA.filter((estado) => estado !== RESERVA_SENADA || tieneSena(reserva))
);

/** Una reserva pendiente, confirmada o señada la puede cancelar el complejo sin restricción horaria. */
export const puedeCancelarElComplejo = (reserva) => ESTADOS_RESERVA_CANCELABLES.includes(reserva.estado);

/** Se reabre una reserva cancelada cuyo turno todavía no empezó. */
export const puedeReabrir = (reserva, ahora = new Date()) => (
  ESTADOS_RESERVA_CANCELADOS.includes(reserva.estado) && !yaComenzo(reserva, ahora)
);

/** Error de las observaciones internas (largo máximo, igual que el servidor) o `undefined`. Vacío es válido: las borra. */
export const errorDeObservaciones = (texto) => {
  const maximo = PARAMETROS.limitesCampos.descripcion;
  return String(texto ?? '').trim().length > maximo ? t('agenda.errorObservaciones', { maximo }) : undefined;
};

/** Si el texto escrito difiere del guardado (sin contar espacios en los extremos). */
export const observacionesModificadas = (reserva, texto) => (
  String(texto ?? '').trim() !== String(reserva.observaciones ?? '').trim()
);

export const VALORES_RESERVA_MANUAL_INICIALES = Object.freeze({
  cancha: '',
  fecha_turno: '',
  hora_inicio: '',
  nombre_cliente_manual: '',
  telefono_cliente_manual: '',
  observaciones: '',
});

/** Errores por campo del alta manual; `hoy` es `AAAA-MM-DD`. Un objeto vacío significa que se puede enviar. */
export const validarReservaManual = (valores, hoy) => {
  const errores = {};
  if (!valores.cancha) errores.cancha = t('agenda.errorCancha');
  if (!parsearFecha(valores.fecha_turno)) errores.fecha_turno = t('agenda.errorFecha');
  else if (valores.fecha_turno < hoy) errores.fecha_turno = t('agenda.errorPasado');
  if (!valores.hora_inicio) errores.hora_inicio = t('agenda.errorHora');
  if (valores.nombre_cliente_manual.trim() === '') errores.nombre_cliente_manual = t('agenda.errorNombre');
  return errores;
};

/** Cuerpo del `POST /api/agenda/`. El horario de fin y el precio los calcula el servidor. */
export const cuerpoReservaManual = (valores) => ({
  cancha: Number(valores.cancha),
  fecha_turno: valores.fecha_turno,
  hora_inicio: valores.hora_inicio,
  nombre_cliente_manual: valores.nombre_cliente_manual.trim(),
  telefono_cliente_manual: valores.telefono_cliente_manual.trim(),
  observaciones: valores.observaciones.trim(),
});
