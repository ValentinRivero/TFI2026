import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

const VALORES = Object.freeze([
  Object.freeze({ icono: 'rayo', clave: 'portada.valorTiempoReal' }),
  Object.freeze({ icono: 'check', clave: 'portada.valorTresPasos' }),
  Object.freeze({ icono: 'escudo', clave: 'portada.valorTransparencia' }),
]);

// Líneas de una cancha genérica (perímetro, línea media, círculo central y áreas): decorativas, sin significado propio.
function FondoCancha() {
  return (
    <svg
      className="hero-cancha"
      viewBox="0 0 480 300"
      aria-hidden="true"
      focusable="false"
      preserveAspectRatio="xMaxYMid meet"
    >
      <rect x="10" y="10" width="460" height="280" rx="4" />
      <path d="M240 10v280" />
      <circle cx="240" cy="150" r="44" />
      <circle cx="240" cy="150" r="2.5" />
      <rect x="10" y="85" width="80" height="130" />
      <rect x="10" y="120" width="32" height="60" />
      <path d="M90 126a44 44 0 010 48" />
      <rect x="390" y="85" width="80" height="130" />
      <rect x="438" y="120" width="32" height="60" />
      <path d="M390 126a44 44 0 000 48" />
    </svg>
  );
}

/**
 * Presentación de la portada: título, bajada, accesos rápidos al buscador y al mapa, y
 * los tres valores del servicio. `children` es el lugar del clima de la ciudad; `onExplorar` y `onAbrirMapa` los
 * resuelve la página (desplazamiento y cambio de vista).
 */
export default function HeroPresentacion({ onExplorar, onAbrirMapa, children }) {
  return (
    <section className="hero-presentacion mb-4" aria-labelledby="hero-titulo">
      <FondoCancha />
      <div className="hero-contenido">
        <h1 id="hero-titulo" className="hero-titulo">{t('portada.titulo')}</h1>
        <p className="hero-bajada">{t('portada.bajada')}</p>

        <div className="d-flex flex-wrap gap-2 mb-4">
          <button type="button" className="btn btn-primary" onClick={onExplorar}>
            <Icono nombre="buscar" tamano={18} />
            {t('portada.explorar')}
          </button>
          <button type="button" className="btn btn-outline-light" onClick={onAbrirMapa}>
            <Icono nombre="mapa" tamano={18} />
            {t('portada.abrirMapa')}
          </button>
        </div>

        <ul className="hero-valores list-unstyled" aria-label={t('portada.valores')}>
          {VALORES.map(({ icono, clave }) => (
            <li key={clave} className="hero-pildora">
              <Icono nombre={icono} tamano={16} />
              {t(clave)}
            </li>
          ))}
        </ul>

        {children && <div className="hero-clima">{children}</div>}
      </div>
    </section>
  );
}
