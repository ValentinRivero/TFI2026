import { t } from '../i18n/index.js';
import CanchaCard from './CanchaCard.jsx';

/** Canchas activas del complejo con su ficha pública. */
export default function SeccionCanchas({ canchas }) {
  return (
    <section className="mb-4" aria-labelledby="detalle-canchas">
      <h2 id="detalle-canchas" className="h4">{t('complejo.canchas')}</h2>
      {canchas.length === 0 ? (
        <p className="text-secondary">{t('complejo.sinCanchas')}</p>
      ) : (
        <div className="row g-3 row-cols-1 row-cols-md-2 row-cols-xl-3">
          {canchas.map((cancha) => (
            <div key={cancha.id} className="col"><CanchaCard cancha={cancha} /></div>
          ))}
        </div>
      )}
    </section>
  );
}
