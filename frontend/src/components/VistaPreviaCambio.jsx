import { describir, ESTADO_RESERVA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaCorta, formatearFechaLarga, formatearHora } from '../utils/formatos.js';

const horario = (texto) => formatearHora(texto);
const rangoHorario = (rango) => t('grilla.resumenHorarioValor', {
  inicio: horario(rango?.hora_inicio),
  fin: horario(rango?.hora_fin),
});

/**
 * Detalle de lo que va a cambiar antes de confirmar, a partir de la `vista_previa` del `409` con
 * `requiere_confirmacion`. Reconoce los dos formatos del backend: la reapertura de una reserva (estado actual y
 * nuevo del turno) y el cambio de horario de un turno fijo (horario actual y nuevo, desde cuándo rige y cuántas
 * fechas ya registradas conservan el anterior). Una vista previa desconocida no muestra nada.
 */
export default function VistaPreviaCambio({ vistaPrevia }) {
  if (!vistaPrevia) return null;

  if ('estado_nuevo' in vistaPrevia) {
    return (
      <dl className="row g-2 mb-3">
        <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.turno')}</dt>
        <dd className="col-7 mb-0 num">
          {formatearFechaLarga(vistaPrevia.fecha_turno)}, {horario(vistaPrevia.hora_inicio)} - {horario(vistaPrevia.hora_fin)}
        </dd>
        <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.estadoActual')}</dt>
        <dd className="col-7 mb-0">{describir(ESTADO_RESERVA, vistaPrevia.estado_actual).etiqueta}</dd>
        <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.estadoNuevo')}</dt>
        <dd className="col-7 mb-0">{describir(ESTADO_RESERVA, vistaPrevia.estado_nuevo).etiqueta}</dd>
      </dl>
    );
  }

  if ('horario_nuevo' in vistaPrevia) {
    const fechas = Array.isArray(vistaPrevia.fechas_registradas) ? vistaPrevia.fechas_registradas : [];
    return (
      <dl className="row g-2 mb-3">
        <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.horarioActual')}</dt>
        <dd className="col-7 mb-0 num">{rangoHorario(vistaPrevia.horario_actual)}</dd>
        <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.horarioNuevo')}</dt>
        <dd className="col-7 mb-0 num">{rangoHorario(vistaPrevia.horario_nuevo)}</dd>
        {vistaPrevia.rige_desde && (
          <>
            <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.rigeDesde')}</dt>
            <dd className="col-7 mb-0 num">{formatearFechaCorta(vistaPrevia.rige_desde)}</dd>
          </>
        )}
        <dt className="col-5 fw-normal text-secondary">{t('vistaPrevia.fechasRegistradas')}</dt>
        <dd className="col-7 mb-0 num">
          {fechas.length === 0 ? t('vistaPrevia.ningunaFecha') : fechas.map((fecha) => formatearFechaCorta(fecha.fecha_turno)).join(', ')}
        </dd>
      </dl>
    );
  }

  return null;
}
