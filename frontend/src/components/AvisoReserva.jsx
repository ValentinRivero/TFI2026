import { Link } from 'react-router-dom';
import { RESULTADO_RESERVA } from '../hooks/useReservaTurno.js';
import { t } from '../i18n/index.js';
import { debeAbonarSena } from '../utils/pagos.js';
import Alerta from './Alerta.jsx';
import TarjetaAlias from './TarjetaAlias.jsx';

/**
 * Resultado de un intento de reserva: confirmada o turno que acaba de ocuparse. Si el complejo exige seña, la reserva
 * confirmada trae el alias para transferirla, con el botón de copiar; siempre ofrece ir a "Mis reservas".
 */
export default function AvisoReserva({ resultado, onCerrar }) {
  if (resultado.tipo === RESULTADO_RESERVA.CREADA) {
    const { reserva } = resultado;
    const conSena = debeAbonarSena(reserva);
    return (
      <Alerta variante="success" titulo={t('reserva.creadaTitulo')} onCerrar={onCerrar}>
        <p className="mb-2">{t(conSena ? 'reserva.creadaSena' : 'reserva.creadaSinSena')}</p>
        {conSena && <TarjetaAlias datos={reserva.datos_transferencia} monto={reserva.monto_sena} className="mb-3" />}
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
