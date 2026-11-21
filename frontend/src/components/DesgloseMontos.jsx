import { formatearPrecio } from '../utils/formatos.js';

/**
 * Montos de un turno en lista de definiciones. `filas` es `[{ clave, etiqueta, importe, destacada }]` (ver
 * `utils/pagos.js`); la fila `destacada` resalta el importe que el jugador o el personal tiene que mirar.
 */
export default function DesgloseMontos({ filas, className = 'mb-0' }) {
  return (
    <dl className={`row g-2 ${className}`.trim()}>
      {filas.map(({ clave, etiqueta, importe, destacada }) => (
        <div key={clave} className="col-12 d-flex justify-content-between gap-3">
          <dt className="fw-normal text-secondary">{etiqueta}</dt>
          <dd className={`mb-0 num${destacada ? ' fw-semibold' : ''}`}>{formatearPrecio(importe)}</dd>
        </div>
      ))}
    </dl>
  );
}
