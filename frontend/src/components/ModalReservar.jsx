import { t } from '../i18n/index.js';
import { pronosticoDeFecha } from '../utils/clima.js';
import Alerta from './Alerta.jsx';
import AvisoSinCancelacion from './AvisoSinCancelacion.jsx';
import ClimaCard from './ClimaCard.jsx';
import DatosTurno from './DatosTurno.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Confirmación de la reserva: turno elegido, pronóstico del día (si entra en la ventana del clima), condiciones de
 * seña y margen de cancelación del complejo. `error` es el `ErrorApi` de un intento rechazado; `onConfirmar` puede
 * devolver una promesa y `ModalConfirmar` evita el doble envío. `horasSinCancelacion` repite la advertencia cuando
 * el turno ya está dentro del margen de cancelación.
 */
export default function ModalReservar({ mostrar, complejo, cancha, bloque, fecha, clima, error, horasSinCancelacion, onConfirmar, onCancelar }) {
  if (!cancha || !bloque) return null;
  const horas = complejo.horas_limite_cancelacion;
  const hayPronostico = Boolean(pronosticoDeFecha(clima.datos, fecha));

  return (
    <ModalConfirmar
      mostrar={mostrar}
      titulo={t('reserva.titulo')}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
      textoConfirmar={t('reserva.confirmar')}
    >
      {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
      {horasSinCancelacion && <AvisoSinCancelacion horas={horasSinCancelacion} />}
      <DatosTurno cancha={cancha} bloque={bloque} fecha={fecha} />
      {hayPronostico && <div className="mb-3"><ClimaCard {...clima} variante="dia" fecha={fecha} /></div>}
      <h3 className="h6">{t('complejo.sena')}</h3>
      <p className="texto-multilinea">
        {complejo.info_sena || <span className="text-secondary">{t('complejo.senaVacia')}</span>}
      </p>
      <h3 className="h6">{t('complejo.cancelacion')}</h3>
      <p className="mb-0">
        {horas > 0 ? t('complejo.cancelacionHoras', { horas }) : t('complejo.cancelacionHasta')}
      </p>
    </ModalConfirmar>
  );
}
