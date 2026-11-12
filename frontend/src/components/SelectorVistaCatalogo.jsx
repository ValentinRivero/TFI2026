import { VISTAS_CATALOGO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

/** Conmutador entre la lista de tarjetas y el mapa. `vista` y `onCambiar` usan el `valor` de `VISTAS_CATALOGO`. */
export default function SelectorVistaCatalogo({ vista, onCambiar }) {
  return (
    <div className="selector-vista" role="group" aria-label={t('catalogo.vistas')}>
      {VISTAS_CATALOGO.map(({ valor, clave, icono }) => {
        const activa = valor === vista;
        return (
          <button
            key={valor}
            type="button"
            className={`btn ${activa ? 'btn-primary' : 'btn-outline-secondary'} d-inline-flex align-items-center justify-content-center gap-2`}
            aria-pressed={activa}
            onClick={() => onCambiar(valor)}
          >
            <Icono nombre={icono} tamano={18} />
            {t(clave)}
          </button>
        );
      })}
    </div>
  );
}
