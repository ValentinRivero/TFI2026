import { t } from '../i18n/index.js';
import CanchaCard from './CanchaCard.jsx';

/**
 * Primer paso de la reserva: las canchas activas del complejo como tarjetas para elegir. `seleccionadaId` es la
 * elegida (o `null`) y `onElegir(id)` avisa la elección; la grilla de turnos muestra solo esa cancha.
 */
export default function SeccionCanchas({ canchas, seleccionadaId, onElegir }) {
  return (
    <section className="mb-4" aria-labelledby="detalle-canchas">
      <h2 id="detalle-canchas" className="h4">{t('complejo.canchas')}</h2>
      {canchas.length === 0 ? (
        <p className="text-secondary">{t('complejo.sinCanchas')}</p>
      ) : (
        <>
          {canchas.length > 1 && <p className="text-secondary">{t('complejo.elegirCancha')}</p>}
          <div className="row g-3 row-cols-1 row-cols-md-2 row-cols-xl-3">
            {canchas.map((cancha) => (
              <div key={cancha.id} className="col">
                <CanchaCard cancha={cancha} seleccionada={cancha.id === seleccionadaId} onElegir={onElegir} />
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
