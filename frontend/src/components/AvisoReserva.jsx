import { Link } from 'react-router-dom';
import { RESULTADO_RESERVA } from '../hooks/useReservaTurno.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';

/** Resultado de un intento de reserva: confirmada (con acceso a "Mis reservas") o turno que acaba de ocuparse. */
export default function AvisoReserva({ resultado, onCerrar }) {
  if (resultado.tipo === RESULTADO_RESERVA.CREADA) {
    return (
      <Alerta variante="success" titulo={t('reserva.creadaTitulo')} onCerrar={onCerrar}>
        <p className="mb-2">{t('reserva.creadaDescripcion')}</p>
        <Link to="/mis-reservas">{t('reserva.verMisReservas')}</Link>
      </Alerta>
    );
  }
  return (
    <Alerta variante="warning" titulo={t('reserva.ocupadoTitulo')} onCerrar={onCerrar}>
      <p className="mb-0">{t('reserva.ocupadoDescripcion')} {resultado.mensaje}</p>
    </Alerta>
  );
}
