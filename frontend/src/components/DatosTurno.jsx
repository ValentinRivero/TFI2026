import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora, formatearPrecio } from '../utils/formatos.js';

/** Cancha, fecha, horario y precio de un turno de la grilla, en lista de definiciones. */
export default function DatosTurno({ cancha, bloque, fecha, className = 'mb-3' }) {
  return (
    <dl className={`row g-2 ${className}`.trim()}>
      <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenCancha')}</dt>
      <dd className="col-8 col-sm-9 mb-0">{cancha.nombre} <span className="text-secondary">({cancha.deporte.nombre})</span></dd>
      <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenFecha')}</dt>
      <dd className="col-8 col-sm-9 mb-0">{formatearFechaLarga(fecha)}</dd>
      <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenHorario')}</dt>
      <dd className="col-8 col-sm-9 mb-0 num">
        {t('grilla.resumenHorarioValor', { inicio: formatearHora(bloque.hora_inicio), fin: formatearHora(bloque.hora_fin) })}
      </dd>
      <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenPrecio')}</dt>
      <dd className="col-8 col-sm-9 mb-0 num fs-5">{formatearPrecio(bloque.precio)}</dd>
    </dl>
  );
}
