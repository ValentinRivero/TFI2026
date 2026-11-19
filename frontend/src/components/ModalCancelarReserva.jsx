import { RESERVA_SENADA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Confirmación de la cancelación de una reserva propia. `reserva` es la elegida (o `null` con el diálogo cerrado) y
 * `error` el `ErrorApi` de un intento rechazado, por ejemplo por margen vencido.
 */
export default function ModalCancelarReserva({ reserva, error, onConfirmar, onCancelar }) {
  return (
    <ModalConfirmar
      mostrar={Boolean(reserva)}
      titulo={t('misReservas.cancelarTitulo')}
      variante="danger"
      textoConfirmar={t('misReservas.cancelarConfirmar')}
      textoCancelar={t('misReservas.cancelarConservar')}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
    >
      {reserva && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p>
            {t('misReservas.cancelarPregunta', {
              complejo: reserva.complejo.nombre,
              cancha: reserva.cancha.nombre,
              fecha: formatearFechaLarga(reserva.fecha_turno),
              inicio: formatearHora(reserva.hora_inicio),
            })}
          </p>
          <p className={reserva.estado === RESERVA_SENADA ? '' : 'mb-0'}>{t('misReservas.cancelarEfecto')}</p>
          {reserva.estado === RESERVA_SENADA &&<p className="mb-0">{t('misReservas.cancelarSena')}</p>}
        </>
      )}
    </ModalConfirmar>
  );
}
