import { t } from '../i18n/index.js';

/**
 * Conmutador flotante entre las capas del mapa (`Mapa` | `Satélite`). `capas` es `PARAMETROS.mapa.capas`; `activa` y
 * `onCambiar` usan el `valor` de cada capa.
 */
export default function ControlCapasMapa({ capas, activa, onCambiar }) {
  return (
    <div className="mapa-control mapa-control-capas" role="group" aria-label={t('mapa.capas')}>
      {Object.values(capas).map(({ valor, clave }) => (
        <button
          key={valor}
          type="button"
          className={`mapa-control-opcion${valor === activa ? ' activa' : ''}`}
          aria-pressed={valor === activa}
          onClick={() => onCambiar(valor)}
        >
          {t(clave)}
        </button>
      ))}
    </div>
  );
}
