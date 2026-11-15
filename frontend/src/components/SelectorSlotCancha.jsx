import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';
import { formatearHora, formatearPrecio } from '../utils/formatos.js';
import CasilleroGrilla from './CasilleroGrilla.jsx';
import Cargando from './Cargando.jsx';

/**
 * Mini-grilla de una cancha en un día para completar una reserva manual: muestra los casilleros reales (libre, ocupado,
 * cerrado por excepción, no disponible) y solo deja elegir los libres. Al elegir uno quedan definidos el horario de inicio,
 * el de fin y el precio sugerido, que calcula el servidor. `bloques` es lo que devuelve `useBloquesDeCancha`; `valor` es
 * la hora de inicio elegida (`HH:MM`) y `onElegir(horaInicio)` avisa la elección.
 */
export default function SelectorSlotCancha({ bloques, valor, onElegir, error }) {
  const elegido = bloques.bloques.find((bloque) => formatearHora(bloque.hora_inicio) === valor);

  return (
    <div role="group" aria-label={t('agenda.horario')}>
      <Form.Label as="span" className="d-block">{t('agenda.horario')}</Form.Label>
      {!bloques.listo && <p className="small text-secondary mb-0">{t('agenda.elegirCanchaYDia')}</p>}
      {bloques.listo && bloques.cargando && <Cargando variante="inline" />}
      {bloques.listo && !bloques.cargando && bloques.error && <p className="small text-danger mb-0">{bloques.error.mensaje}</p>}
      {bloques.listo && !bloques.cargando && !bloques.error && bloques.bloques.length === 0 && (
        <p className="small text-secondary mb-0">{t('agenda.sinBloques')}</p>
      )}
      {bloques.listo && !bloques.error && bloques.bloques.length > 0 && (
        <>
          <div className="grilla-compacta">
            {bloques.bloques.map((bloque) => (
              <CasilleroGrilla
                key={bloque.hora_inicio}
                bloque={bloque}
                seleccionado={formatearHora(bloque.hora_inicio) === valor && bloque.estado === 'LIBRE'}
                onElegir={() => onElegir(formatearHora(bloque.hora_inicio))}
              />
            ))}
          </div>
          {elegido && (
            <p className="small mt-2 mb-0 num" role="status">
              {t('agenda.turnoElegido', {
                inicio: formatearHora(elegido.hora_inicio),
                fin: formatearHora(elegido.hora_fin),
                precio: formatearPrecio(elegido.precio),
              })}
            </p>
          )}
        </>
      )}
      {error && <div className="text-danger small mt-1">{error}</div>}
    </div>
  );
}
