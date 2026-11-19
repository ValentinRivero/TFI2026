import Form from 'react-bootstrap/Form';
import CampoFecha from './CampoFecha.jsx';

/**
 * Campo de formulario con etiqueta, ayuda y mensaje de error por campo. `onCambiar` recibe el valor (no el evento);
 * el resto de las propiedades (`type`, `autoComplete`, `maxLength`...) pasan al control. Con `type="date"` delega en
 * `CampoFecha`: la fecha se ve siempre como `dd/mm/aaaa` y el valor viaja como `AAAA-MM-DD`.
 */
export default function CampoFormulario({ id, etiqueta, valor, onCambiar, error, ayuda, className = 'mb-3', ...control }) {
  if (control.type === 'date') {
    const { type: _tipo, ...resto } = control;
    return (
      <CampoFecha id={id} etiqueta={etiqueta} valor={valor} onCambiar={onCambiar} error={error} ayuda={ayuda} className={className} {...resto} />
    );
  }

  return (
    <Form.Group className={className} controlId={id}>
      <Form.Label>{etiqueta}</Form.Label>
      <Form.Control
        value={valor}
        onChange={(evento) => onCambiar(evento.target.value)}
        isInvalid={Boolean(error)}
        {...control}
      />
      <Form.Control.Feedback type="invalid">{error}</Form.Control.Feedback>
      {ayuda && <Form.Text muted>{ayuda}</Form.Text>}
    </Form.Group>
  );
}
