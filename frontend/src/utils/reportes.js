import { CONTEO_REPORTE_POR_ESTADO, CRITERIO_REPORTE_POR_DEFECTO } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { diasEntre, parsearFecha } from './formatos.js';

/** Rango inicial del dashboard: desde el primer día del mes en curso hasta hoy (`hoy` es `AAAA-MM-DD`). */
export const filtrosReporteIniciales = (hoy) => ({
  fecha_desde: `${hoy.slice(0, 8)}01`,
  fecha_hasta: hoy,
  criterio: CRITERIO_REPORTE_POR_DEFECTO,
  cancha: '',
  deporte: '',
});

/** Errores por campo de los filtros; un objeto vacío significa que se puede consultar. */
export const validarFiltrosReporte = (filtros) => {
  const errores = {};
  const maximo = PARAMETROS.reportes.rangoMaximoDias;
  if (!parsearFecha(filtros.fecha_desde)) errores.fecha_desde = t('reportes.errorFecha');
  if (!parsearFecha(filtros.fecha_hasta)) errores.fecha_hasta = t('reportes.errorFecha');
  if (!errores.fecha_desde && !errores.fecha_hasta) {
    const dias = diasEntre(filtros.fecha_desde, filtros.fecha_hasta);
    if (dias < 0) errores.fecha_hasta = t('reportes.errorOrden');
    else if (dias + 1 > maximo) errores.fecha_hasta = t('reportes.errorRango', { maximo });
  }
  return errores;
};

/** Parámetros de `GET /api/reportes/dashboard/`; la cancha y el deporte vacíos no viajan. */
export const aParametrosReporte = (complejoId, filtros) => {
  const params = {
    complejo: complejoId,
    fecha_desde: filtros.fecha_desde,
    fecha_hasta: filtros.fecha_hasta,
    criterio: filtros.criterio,
  };
  if (filtros.cancha) params.cancha_id = filtros.cancha;
  if (filtros.deporte) params.deporte_id = filtros.deporte;
  return params;
};

/** Total de reservas del rango: la suma de todos los estados (las canceladas cuentan una sola vez). */
export const totalReservas = (conteos) => (
  CONTEO_REPORTE_POR_ESTADO.reduce((suma, { clave }) => suma + (Number(conteos?.[clave]) || 0), 0)
);

/** Porcentaje de reservas canceladas (por el jugador y por el complejo) sobre el total; 0 si no hay reservas. */
export const tasaCancelacion = (conteos) => {
  const total = totalReservas(conteos);
  if (total === 0) return 0;
  return ((Number(conteos.canceladas_jugador) || 0) + (Number(conteos.canceladas_complejo) || 0)) / total * 100;
};

/** Filas del desglose por estado, en el orden de los códigos de estado de reserva. */
export const filasDeConteo = (conteos) => (
  CONTEO_REPORTE_POR_ESTADO.map(({ clave, estado }) => ({ clave, estado, cantidad: Number(conteos?.[clave]) || 0 }))
);

/** Ancho de una barra proporcional (0 a 100) de `valor` respecto de `maximo`; sin máximo positivo, 0. */
export const anchoDeBarra = (valor, maximo) => {
  const numero = Number(valor);
  if (!Number.isFinite(numero) || !(maximo > 0)) return 0;
  return Math.min(100, Math.max(0, (numero / maximo) * 100));
};

/** Mayor valor de un campo numérico en una lista; 0 si está vacía. */
export const maximoDe = (lista, campo) => (
  (lista ?? []).reduce((mayor, item) => Math.max(mayor, Number(item[campo]) || 0), 0)
);
