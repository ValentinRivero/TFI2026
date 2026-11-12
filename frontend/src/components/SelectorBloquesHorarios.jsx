import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';
import { formatearHora, formatearPrecio } from '../utils/formatos.js';
import Cargando from './Cargando.jsx';

/**
 * Elección del horario de un turno fijo entre los bloques válidos de la cancha ese día de la semana, sin escribir
 * minutos a mano. `bloques` es lo que devuelve `useBloquesDeHorario`; `valor` es la hora de inicio elegida (`HH:MM`) y
 * `onElegir(horaInicio)` avisa la elección. `error` es el mensaje de validación del campo.
 */
export default function SelectorBloquesHorarios({ bloques, valor, onElegir, error, etiqueta = t('turnosFijos.horario') }) {
  const { listo, cargando } = bloques;

  return (
    <div role="group" aria-label={etiqueta}>
      <Form.Label as="span" className="d-block">{etiqueta}</Form.Label>
      {!listo && <p className="small text-secondary mb-0">{t('turnosFijos.elegirCanchaYDia')}</p>}
      {listo && cargando && <Cargando variante="inline" />}
      {listo && !cargando && bloques.error && <p className="small text-danger mb-0">{bloques.error.mensaje}</p>}
      {listo && !cargando && !bloques.error && bloques.bloques.length === 0 && (
        <p className="small text-secondary mb-0">{t('turnosFijos.sinBloques')}</p>
      )}
      {listo && !cargando && !bloques.error && bloques.bloques.length > 0 && (
        <div className="d-flex flex-wrap gap-2">
          {bloques.bloques.map((bloque) => {
            const elegido = valor === bloque.hora_inicio;
            return (
              <Button
                key={bloque.hora_inicio}
                size="sm"
                variant={elegido ? 'primary' : 'outline-secondary'}
                aria-pressed={elegido}
                className="num"
                onClick={() => onElegir(bloque.hora_inicio)}
              >
                {t('grilla.resumenHorarioValor', { inicio: formatearHora(bloque.hora_inicio), fin: formatearHora(bloque.hora_fin) })}
                {bloque.precio ? <span className="ms-2 small">{formatearPrecio(bloque.precio)}</span> : null}
              </Button>
            );
          })}
        </div>
      )}
      {error && <div className="text-danger small mt-1">{error}</div>}
    </div>
  );
}
