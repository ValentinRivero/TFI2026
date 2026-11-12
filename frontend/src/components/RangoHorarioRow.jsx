import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';

/**
 * Un rango de apertura de un día: apertura, cierre y precio diferenciado opcional. `errores` trae un texto por campo
 * (`hora_apertura`, `hora_cierre`, `precio_diferenciado`); `descripcion` rotula los controles para lectores de pantalla.
 * Con `soloLectura` los valores se muestran sin poder cambiarse. Los cambios llegan como `onCambiar(campo, valor)`.
 */
export default function RangoHorarioRow({ fila, errores = {}, descripcion, soloLectura, onCambiar, onQuitar }) {
  const control = (campo, etiqueta, propiedades) => (
    <Form.Group controlId={`${fila.clave}-${campo}`} className="rango-campo">
      <Form.Label className="small text-secondary mb-1">{etiqueta}</Form.Label>
      <Form.Control
        size="sm"
        value={fila[campo]}
        readOnly={soloLectura}
        isInvalid={Boolean(errores[campo])}
        aria-label={`${etiqueta} - ${descripcion}`}
        onChange={(evento) => onCambiar(fila.clave, campo, evento.target.value)}
        {...propiedades}
      />
      <Form.Control.Feedback type="invalid">{errores[campo]}</Form.Control.Feedback>
    </Form.Group>
  );

  return (
    <div className="rango-horario d-flex flex-wrap align-items-start gap-2">
      {control('hora_apertura', t('horarios.apertura'), { type: 'time', className: 'num' })}
      {control('hora_cierre', t('horarios.cierre'), { type: 'time', className: 'num' })}
      {control('precio_diferenciado', t('horarios.precio'), {
        inputMode: 'decimal',
        placeholder: t('horarios.usaPrecioBase'),
        className: 'num',
      })}
      {!soloLectura && (
        <Button size="sm" variant="outline-danger" className="align-self-end" onClick={() => onQuitar(fila.clave)}>
          {t('horarios.quitar')}
        </Button>
      )}
    </div>
  );
}
