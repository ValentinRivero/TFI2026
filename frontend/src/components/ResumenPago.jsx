import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';
import { estadoReflejaElPago, muestraSeguimientoDePago, transferenciaParaRevisar, transferenciaRechazada } from '../utils/pagos.js';
import BadgeEstadoPago from './BadgeEstadoPago.jsx';
import DatosTransferenciaInformada from './DatosTransferenciaInformada.jsx';

/**
 * Precio de la reserva y, si hay seña acordada o algo abonado, su estado de pago con lo abonado y el saldo. Si el
 * jugador informó una transferencia que todavía no se confirmó, la marca y muestra sus datos para revisarla.
 */
export default function ResumenPago({ reserva }) {
  return (
    <>
      <div>{formatearPrecio(reserva.precio_acordado)}</div>
      {muestraSeguimientoDePago(reserva) && (
        <>
          {!estadoReflejaElPago(reserva) && <div className="my-1"><BadgeEstadoPago reserva={reserva} /></div>}
          <div className="small text-secondary">{t('pagos.pagado')}: {formatearPrecio(reserva.monto_pagado)}</div>
          <div className="small text-secondary">{t('pagos.saldoRestante')}: {formatearPrecio(reserva.saldo_restante)}</div>
        </>
      )}
      {transferenciaRechazada(reserva) && reserva.puede_confirmar_sena && (
        <div className="mt-2">
          <span className="badge badge-peligro">{t('transferencia.rechazada')}</span>
          <div className="small text-secondary mt-1">{reserva.transferencia.rechazo.motivo_nombre}</div>
        </div>
      )}
      {transferenciaParaRevisar(reserva) && (
        <div className="mt-2">
          <span className="badge badge-info">{t('transferencia.informada')}</span>
          <DatosTransferenciaInformada transferencia={reserva.transferencia} compacto className="mt-1" />
        </div>
      )}
    </>
  );
}
