import Button from 'react-bootstrap/Button';
import useCopiar from '../hooks/useCopiar.js';
import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';
import Icono from './Icono.jsx';

/**
 * Datos para transferir la seña de una reserva: alias del complejo con el botón "Copiar alias" y, si lo informó, el
 * titular de la cuenta. `monto` es la seña a transferir. El resultado de copiar se anuncia a lectores de pantalla.
 */
export default function TarjetaAlias({ datos, monto, className = '' }) {
  const { copiar, copiado, fallo } = useCopiar(datos.alias);

  return (
    <section className={`superficie p-3 ${className}`.trim()} aria-label={t('pagos.tarjetaTitulo')}>
      <h4 className="h6">{t('pagos.tarjetaTitulo')}</h4>
      <p className="small text-secondary">{t('pagos.tarjetaAyuda', { monto: formatearPrecio(monto) })}</p>
      <div className="d-flex flex-wrap align-items-center gap-3">
        <div>
          <div className="small text-secondary">{t('pagos.alias')}</div>
          <strong className="fs-5 alias-transferencia">{datos.alias}</strong>
        </div>
        <Button variant={copiado ? 'success' : 'outline-primary'} onClick={copiar}>
          <Icono nombre={copiado ? 'check' : 'copiar'} />
          {copiado ? t('pagos.aliasCopiado') : t('pagos.copiarAlias')}
        </Button>
      </div>
      {datos.titular && (
        <p className="small mt-2 mb-0">
          <span className="text-secondary">{t('pagos.titular')}: </span>{datos.titular}
        </p>
      )}
      <p role="status" className={fallo ? 'small text-danger mt-2 mb-0' : 'visually-hidden'}>
        {copiado && t('pagos.aliasCopiado')}
        {fallo && t('pagos.errorCopiar')}
      </p>
    </section>
  );
}
