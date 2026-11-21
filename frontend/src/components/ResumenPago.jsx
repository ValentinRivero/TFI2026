import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';
import { estadoReflejaElPago, muestraSeguimientoDePago } from '../utils/pagos.js';
import BadgeEstadoPago from './BadgeEstadoPago.jsx';

/** Precio de la reserva y, si hay seña acordada o algo abonado, su estado de pago con lo abonado y el saldo. */
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
    </>
  );
}
