import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora, formatearPrecio } from '../utils/formatos.js';

/**
 * Resumen del turno elegido en la grilla. `onConfirmar` queda para el flujo de reserva: sin él, el botón de
 * confirmar se muestra deshabilitado. `children` es el lugar del pronóstico del día.
 */
export default function ResumenTurno({ cancha, bloque, fecha, onConfirmar, onQuitar, children }) {
  return (
    <section className="superficie p-3" aria-labelledby="resumen-turno-titulo" aria-live="polite">
      <h3 id="resumen-turno-titulo" className="h5">{t('grilla.resumenTitulo')}</h3>
      <dl className="row g-2 mb-3">
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenCancha')}</dt>
        <dd className="col-8 col-sm-9 mb-0">{cancha.nombre} <span className="text-secondary">({cancha.deporte.nombre})</span></dd>
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenFecha')}</dt>
        <dd className="col-8 col-sm-9 mb-0 text-capitalize">{formatearFechaLarga(fecha)}</dd>
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenHorario')}</dt>
        <dd className="col-8 col-sm-9 mb-0 num">
          {t('grilla.resumenHorarioValor', { inicio: formatearHora(bloque.hora_inicio), fin: formatearHora(bloque.hora_fin) })}
        </dd>
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenPrecio')}</dt>
        <dd className="col-8 col-sm-9 mb-0 num fs-5">{formatearPrecio(bloque.precio)}</dd>
      </dl>
      {children && <div className="mb-3">{children}</div>}
      <div className="d-flex flex-wrap gap-2">
        <Button variant="primary" disabled={!onConfirmar} onClick={onConfirmar}>{t('grilla.confirmar')}</Button>
        <Button variant="outline-secondary" onClick={onQuitar}>{t('grilla.quitar')}</Button>
      </div>
    </section>
  );
}
