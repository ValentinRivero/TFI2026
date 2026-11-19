import Button from 'react-bootstrap/Button';
import { Link } from 'react-router-dom';
import { describir, ESTADO_RESERVA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora, formatearMomento, formatearPrecio } from '../utils/formatos.js';
import { CANCELACION, estadoDeCancelacion } from '../utils/reservas.js';
import ContactoComplejo from './ContactoComplejo.jsx';

/**
 * Una reserva propia: complejo (con enlace a su ficha), cancha, deporte, fecha, horario, precio acordado y estado.
 * Si está activa y dentro del margen del complejo ofrece cancelarla (`onCancelar`); si el margen ya pasó, explica el
 * motivo y muestra el teléfono del complejo.
 */
export default function ReservaRow({ reserva, onCancelar }) {
  const { etiqueta, badge } = describir(ESTADO_RESERVA, reserva.estado);
  const cancelacion = estadoDeCancelacion(reserva);

  return (
    <article className="superficie p-3">
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
        <h3 className="h5 mb-0">
          <Link to={`/complejos/${reserva.complejo.id}`}>{reserva.complejo.nombre}</Link>
        </h3>
        <span className={`badge ${badge}`}>{etiqueta}</span>
      </div>
      <p className="mb-2">
        {reserva.cancha.nombre} <span className="text-secondary">({reserva.deporte})</span>
      </p>
      <dl className="row g-2 mb-0">
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenFecha')}</dt>
        <dd className="col-8 col-sm-9 mb-0">{formatearFechaLarga(reserva.fecha_turno)}</dd>
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenHorario')}</dt>
        <dd className="col-8 col-sm-9 mb-0 num">
          {t('grilla.resumenHorarioValor', {
            inicio: formatearHora(reserva.hora_inicio),
            fin: formatearHora(reserva.hora_fin),
          })}
        </dd>
        <dt className="col-4 col-sm-3 fw-normal text-secondary">{t('grilla.resumenPrecio')}</dt>
        <dd className="col-8 col-sm-9 mb-0 num">{formatearPrecio(reserva.precio_acordado)}</dd>
      </dl>

      {cancelacion === CANCELACION.PERMITIDA && (
        <div className="d-flex flex-wrap align-items-center gap-3 mt-3">
          <Button variant="outline-danger" onClick={() => onCancelar(reserva)}>{t('misReservas.cancelar')}</Button>
          <span className="small text-secondary">
            {t('misReservas.cancelableHasta', { momento: formatearMomento(reserva.cancelable_hasta) })}
          </span>
        </div>
      )}

      {cancelacion === CANCELACION.FUERA_DE_MARGEN && (
        <p className="small text-secondary mt-3 mb-0">
          {t('misReservas.fueraDeMargen', { momento: formatearMomento(reserva.cancelable_hasta) })}{' '}
          <ContactoComplejo complejoId={reserva.complejo.id} />
        </p>
      )}
    </article>
  );
}
