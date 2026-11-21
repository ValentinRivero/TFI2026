import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';
import FilaCopiable from './FilaCopiable.jsx';

/**
 * Datos para transferir la seña de una reserva: alias del complejo y, si lo informó, su CBU o CVU como otra forma de
 * transferir, cada uno con su botón de copiar, y el titular de la cuenta. `monto` es la seña a transferir.
 */
export default function TarjetaAlias({ datos, monto, className = '' }) {
  return (
    <section className={`superficie p-3 ${className}`.trim()} aria-label={t('pagos.tarjetaTitulo')}>
      <h4 className="h6">{t('pagos.tarjetaTitulo')}</h4>
      <p className="small text-secondary">
        {t(datos.cbu ? 'pagos.tarjetaAyudaConCbu' : 'pagos.tarjetaAyuda', { monto: formatearPrecio(monto) })}
      </p>
      <FilaCopiable etiqueta={t('pagos.alias')} valor={datos.alias} textoBoton={t('pagos.copiarAlias')} />
      {datos.cbu && (
        <FilaCopiable etiqueta={t('pagos.cbu')} valor={datos.cbu} textoBoton={t('pagos.copiarCbu')} className="mt-3" />
      )}
      {datos.titular && (
        <p className="small mt-3 mb-0">
          <span className="text-secondary">{t('pagos.titular')}: </span>{datos.titular}
        </p>
      )}
    </section>
  );
}
