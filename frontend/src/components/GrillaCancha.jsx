import { t } from '../i18n/index.js';
import CasilleroGrilla from './CasilleroGrilla.jsx';

/**
 * Bloques de una cancha en el día. `seleccionHora` es la hora de inicio elegida en esta cancha (o `null`) y
 * `onElegir(bloque)` avisa la elección.
 */
export default function GrillaCancha({ cancha, seleccionHora, onElegir }) {
  const idTitulo = `grilla-cancha-${cancha.id}`;

  return (
    <section className="superficie p-3" aria-labelledby={idTitulo}>
      <div className="d-flex flex-wrap align-items-baseline gap-2 mb-2">
        <h3 id={idTitulo} className="h5 mb-0">{cancha.nombre}</h3>
        <span className="badge badge-info">{cancha.deporte.nombre}</span>
        <span className="small text-secondary num">{t('grilla.minutos', { minutos: cancha.duracion_turno_min })}</span>
      </div>
      {cancha.bloques.length === 0 ? (
        <p className="text-secondary small mb-0">{t('grilla.sinBloques')}</p>
      ) : (
        <div className="d-flex flex-wrap gap-2">
          {cancha.bloques.map((bloque) => (
            <CasilleroGrilla
              key={bloque.hora_inicio}
              bloque={bloque}
              seleccionado={seleccionHora === bloque.hora_inicio}
              onElegir={() => onElegir(bloque)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
