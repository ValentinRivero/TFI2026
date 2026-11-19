import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

const VALORES = Object.freeze([
  Object.freeze({ icono: 'rayo', clave: 'portada.valorTiempoReal' }),
  Object.freeze({ icono: 'check', clave: 'portada.valorTresPasos' }),
  Object.freeze({ icono: 'escudo', clave: 'portada.valorTransparencia' }),
]);

/*
 * Cancha de fútbol genérica en vista cenital, decorativa y sin significado propio. Proporción 400 x 260 (la de una
 * cancha reglamentaria de 105 x 68 m): perímetro, línea media, círculo central, áreas grande y chica, punto penal,
 * medialuna de cada área y arcos de córner. La mitad derecha es el espejo exacto de la izquierda.
 */
function FondoCancha() {
  return (
    <svg
      className="hero-cancha"
      viewBox="0 0 400 260"
      aria-hidden="true"
      focusable="false"
      preserveAspectRatio="xMaxYMid meet"
    >
      <rect x="4" y="4" width="392" height="252" />
      <path d="M200 4v252" />
      <circle cx="200" cy="130" r="36" />
      <circle className="hero-cancha-punto" cx="200" cy="130" r="2.5" />

      <rect x="4" y="52" width="62" height="156" />
      <rect x="4" y="96" width="21" height="68" />
      <circle className="hero-cancha-punto" cx="45" cy="130" r="2.5" />
      <path d="M66 103.3A34 34 0 0 1 66 156.7" />

      <rect x="334" y="52" width="62" height="156" />
      <rect x="375" y="96" width="21" height="68" />
      <circle className="hero-cancha-punto" cx="355" cy="130" r="2.5" />
      <path d="M334 103.3A34 34 0 0 0 334 156.7" />

      <path d="M12 4A8 8 0 0 1 4 12" />
      <path d="M4 248A8 8 0 0 1 12 256" />
      <path d="M396 12A8 8 0 0 1 388 4" />
      <path d="M388 256A8 8 0 0 1 396 248" />
    </svg>
  );
}

/**
 * Presentación de la portada: título, bajada, accesos rápidos al buscador y al mapa, y los tres valores del
 * servicio. Es una sección de ancho completo (la página la renderiza fuera del contenedor del resto del contenido);
 * su texto se alinea con la misma grilla horizontal gracias al `container` interno. `children` es el lugar del clima
 * de la ciudad; `onExplorar` y `onAbrirMapa` los resuelve la página (desplazamiento y cambio de vista).
 */
export default function HeroPresentacion({ onExplorar, onAbrirMapa, children }) {
  return (
    <section className="hero-presentacion" aria-labelledby="hero-titulo">
      <FondoCancha />
      <div className="container">
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
      </div>
    </section>
  );
}
