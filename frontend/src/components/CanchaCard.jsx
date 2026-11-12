import { t } from '../i18n/index.js';
import { describirCancha } from '../utils/cancha.js';
import { formatearPrecio } from '../utils/formatos.js';

function Dato({ titulo, children }) {
  return (
    <div className="col-6">
      <dt className="small text-secondary fw-normal">{titulo}</dt>
      <dd className="mb-0">{children}</dd>
    </div>
  );
}

/**
 * Ficha pública de una cancha activa: deporte, superficie, cobertura, iluminación, duración del turno y precio base.
 * Con `onElegir` es una tarjeta interactiva (paso previo a la grilla): `seleccionada` la resalta y la anuncia como
 * pulsada. Sin `onElegir` es solo informativa.
 */
export default function CanchaCard({ cancha, seleccionada = false, onElegir }) {
  const { superficie, cobertura, iluminacion, duracion } = describirCancha(cancha);
  const interactiva = Boolean(onElegir);

  const alTeclear = (evento) => {
    if (evento.key === 'Enter' || evento.key === ' ') {
      evento.preventDefault();
      onElegir(cancha.id);
    }
  };

  return (
    <article
      className={`card h-100${interactiva ? ' cancha-opcion' : ''}${seleccionada ? ' cancha-opcion-activa' : ''}`}
      {...(interactiva && {
        role: 'button',
        tabIndex: 0,
        'aria-pressed': seleccionada,
        onClick: () => onElegir(cancha.id),
        onKeyDown: alTeclear,
      })}
    >
      <div className="card-body">
        <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
          <h3 className="h5 mb-0">{cancha.nombre}</h3>
          <span className="d-flex flex-wrap gap-1">
            {seleccionada && <span className="badge badge-ok">{t('cancha.seleccionada')}</span>}
            {cancha.deporte && <span className="badge badge-info">{cancha.deporte.nombre}</span>}
          </span>
        </div>
        <dl className="row g-3 mb-0">
          <Dato titulo={t('cancha.superficie')}>{superficie}</Dato>
          <Dato titulo={t('cancha.cobertura')}>{cobertura}</Dato>
          <Dato titulo={t('cancha.iluminacion')}>{iluminacion}</Dato>
          <Dato titulo={t('cancha.turno')}><span className="num">{duracion}</span></Dato>
          <Dato titulo={t('cancha.precio')}>
            <span className="num fs-5">{formatearPrecio(cancha.precio_base)}</span> {t('cancha.porTurno')}
          </Dato>
        </dl>
      </div>
    </article>
  );
}
