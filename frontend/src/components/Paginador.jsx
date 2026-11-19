import { t } from '../i18n/index.js';
import { ventanaDePaginas } from '../utils/paginacion.js';

/**
 * Paginador de las tablas: "Anterior", accesos directos a 5 páginas y "Siguiente". En la primera página no aparece
 * "Anterior" y en la última no aparece "Siguiente"; la página actual se resalta y no se puede pulsar. Se coloca
 * arriba y abajo de la lista. `alineacion` admite `centro` (por defecto) o `izquierda`.
 */
export default function Paginador({ pagina, total, onCambiar, alineacion = 'centro', className = '' }) {
  if (total <= 1) return null;

  const alineada = alineacion === 'izquierda' ? 'justify-content-start' : 'justify-content-center';

  return (
    <nav aria-label={t('paginador.navegacion')} className={className}>
      <ul className={`pagination flex-wrap mb-0 ${alineada}`}>
        {pagina > 1 && (
          <li className="page-item">
            <button type="button" className="page-link" onClick={() => onCambiar(pagina - 1)}>
              {t('paginador.anterior')}
            </button>
          </li>
        )}
        {ventanaDePaginas(pagina, total).map((numero) => (
          numero === pagina ? (
            <li key={numero} className="page-item active" aria-current="page">
              <span className="page-link" aria-label={t('paginador.paginaActual', { pagina: numero })}>{numero}</span>
            </li>
          ) : (
            <li key={numero} className="page-item">
              <button
                type="button"
                className="page-link"
                aria-label={t('paginador.pagina', { pagina: numero })}
                onClick={() => onCambiar(numero)}
              >
                {numero}
              </button>
            </li>
          )
        ))}
        {pagina < total && (
          <li className="page-item">
            <button type="button" className="page-link" onClick={() => onCambiar(pagina + 1)}>
              {t('paginador.siguiente')}
            </button>
          </li>
        )}
      </ul>
    </nav>
  );
}
