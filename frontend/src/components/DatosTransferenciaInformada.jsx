import { t } from '../i18n/index.js';
import { formatearFechaHora } from '../utils/formatos.js';

/**
 * Lo que el jugador informó al transferir la seña: quién transfirió, el número de operación y cuándo avisó. Lo ve
 * solo el propio jugador y el personal del complejo. Con `compacto` se muestra como líneas cortas «etiqueta: valor»,
 * que se adaptan al ancho de una celda de la agenda (también en la vista apilada de pantallas chicas).
 */
export default function DatosTransferenciaInformada({ transferencia, compacto = false, className = '' }) {
  const filas = [
    { clave: 'quien', etiqueta: t('transferencia.quien'), valor: transferencia.titular, numerico: false },
    { clave: 'operacion', etiqueta: t('transferencia.operacion'), valor: transferencia.referencia, numerico: true },
    { clave: 'informada', etiqueta: t('transferencia.informadaEl'), valor: formatearFechaHora(transferencia.informada_en), numerico: true },
  ];

  if (compacto) {
    return (
      <div className={`small text-secondary ${className}`.trim()}>
        {filas.map(({ clave, etiqueta, valor, numerico }) => (
          <div key={clave}>
            {etiqueta}: <span className={`text-body${numerico ? ' num' : ''}`}>{valor}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <dl className={`row g-1 mb-0 ${className}`.trim()}>
      {filas.map(({ clave, etiqueta, valor, numerico }) => (
        <div key={clave} className="col-12 d-flex justify-content-between gap-3">
          <dt className="fw-normal text-secondary">{etiqueta}</dt>
          <dd className={`mb-0 text-end${numerico ? ' num' : ''}`}>{valor}</dd>
        </div>
      ))}
    </dl>
  );
}
