import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { debeAbonarSena, senaConfirmada, transferenciaRechazada } from '../utils/pagos.js';
import Alerta from './Alerta.jsx';
import DatosTransferenciaInformada from './DatosTransferenciaInformada.jsx';

/**
 * Transferencia de la seña vista por el jugador, junto a la tarjeta del alias. Mientras la seña está pendiente ofrece
 * informarla (o corregirla, si ya la informó) y la marca «a la espera de la confirmación»; con la seña ya confirmada
 * o pagada muestra en solo lectura lo que había informado, sin esa leyenda. Sin nada que informar ni informado no
 * ocupa lugar. Si el complejo rechazó lo informado, muestra el motivo y la nota y ofrece volver a informarla.
 * `onInformar` abre el diálogo de la reserva.
 */
export default function SeccionTransferencia({ reserva, onInformar, className = '' }) {
  const informada = Boolean(reserva.transferencia_informada);
  const editable = debeAbonarSena(reserva);
  const confirmada = senaConfirmada(reserva);
  const rechazada = transferenciaRechazada(reserva);
  const rechazo = reserva.transferencia?.rechazo;
  if (!informada && !editable) return null;

  return (
    <section className={`superficie p-3 ${className}`.trim()} aria-label={t('transferencia.informada')}>
      {informada ? (
        <>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <h4 className="h6 mb-0">{t('transferencia.informada')}</h4>
            {editable && !rechazada && <span className="badge badge-info">{t('transferencia.enRevision')}</span>}
            {editable && rechazada && <span className="badge badge-peligro">{t('transferencia.rechazada')}</span>}
            {confirmada && <span className="badge badge-ok">{t('transferencia.confirmada')}</span>}
          </div>
          {rechazada && rechazo && (
            <Alerta variante="warning" titulo={t('transferencia.rechazadaTitulo')} className="mb-3">
              <p className="mb-1">{rechazo.motivo_nombre}</p>
              {rechazo.nota && <p className="mb-1 texto-multilinea">{rechazo.nota}</p>}
              <p className="mb-0 small">{t('transferencia.rechazadaAyuda')}</p>
            </Alerta>
          )}
          <DatosTransferenciaInformada transferencia={reserva.transferencia} />
        </>
      ) : (
        <p className="small text-secondary">{t('transferencia.invitacion')}</p>
      )}
      {editable && (
        <Button variant={informada && !rechazada ? 'outline-secondary' : 'primary'} className="mt-3" onClick={() => onInformar(reserva)}>
          {t(rechazada ? 'transferencia.volverAInformar' : informada ? 'transferencia.corregir' : 'transferencia.informar')}
        </Button>
      )}
    </section>
  );
}
