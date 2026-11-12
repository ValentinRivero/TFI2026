import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { t } from '../i18n/index.js';
import { formatearEntero, formatearPorcentaje, formatearPrecio } from '../utils/formatos.js';
import { tasaCancelacion, totalReservas } from '../utils/reportes.js';
import TarjetaMetrica from './TarjetaMetrica.jsx';

/**
 * Tarjetas de resumen del dashboard: recaudación (y la parte señada), cantidad de reservas del rango y tasa de
 * cancelación. `dashboard` es la respuesta de `GET /api/reportes/dashboard/`; la tasa y el total se derivan de los conteos.
 */
export default function ResumenReporte({ dashboard }) {
  const { recaudacion, conteos } = dashboard;

  return (
    <Row className="g-3 mb-4">
      <Col sm={6} xl={3}>
        <TarjetaMetrica
          etiqueta={t('reportes.recaudacion')}
          valor={formatearPrecio(recaudacion.total) || formatearPrecio(0)}
          detalle={t('reportes.recaudacionDetalle')}
        />
      </Col>
      <Col sm={6} xl={3}>
        <TarjetaMetrica
          etiqueta={t('reportes.senada')}
          valor={formatearPrecio(recaudacion.senada) || formatearPrecio(0)}
          detalle={t('reportes.senadaDetalle')}
        />
      </Col>
      <Col sm={6} xl={3}>
        <TarjetaMetrica etiqueta={t('reportes.totalReservas')} valor={formatearEntero(totalReservas(conteos))} />
      </Col>
      <Col sm={6} xl={3}>
        <TarjetaMetrica
          etiqueta={t('reportes.tasaCancelacion')}
          valor={formatearPorcentaje(tasaCancelacion(conteos))}
          detalle={t('reportes.tasaDetalle', { cantidad: formatearEntero(conteos.canceladas_total) })}
        />
      </Col>
    </Row>
  );
}
