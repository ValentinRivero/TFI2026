import { t } from '../i18n/index.js';
import GrillaCancha from './GrillaCancha.jsx';

/**
 * Canchas de un día con sus casilleros. Solo dibuja: la elección vive en la página y llega por `seleccion`
 * (`{ canchaId, horaInicio }`) y `onElegir(cancha, bloque)`. Elegir de nuevo el bloque elegido lo quita.
 */
export default function GrillaDia({ grilla, seleccion, onElegir }) {
  if (grilla.canchas.length === 0) {
    return <p className="text-secondary mb-0">{t('grilla.sinCanchas')}</p>;
  }

  return (
    <div className="d-grid gap-3">
      {grilla.canchas.map((cancha) => (
        <GrillaCancha
          key={cancha.id}
          cancha={cancha}
          seleccionHora={seleccion?.canchaId === cancha.id ? seleccion.horaInicio : null}
          onElegir={(bloque) => onElegir(cancha, bloque)}
        />
      ))}
    </div>
  );
}
