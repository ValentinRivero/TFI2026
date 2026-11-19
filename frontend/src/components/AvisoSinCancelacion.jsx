import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';

/** Advertencia de que el turno elegido ya está dentro del margen de cancelación: una vez reservado, solo el complejo lo resuelve. */
export default function AvisoSinCancelacion({ horas, className = '' }) {
  return (
    <Alerta variante="warning" titulo={t('reserva.sinCancelacionTitulo')} className={className}>
      <p className="mb-0">{t('reserva.sinCancelacionDescripcion', { horas })}</p>
    </Alerta>
  );
}
