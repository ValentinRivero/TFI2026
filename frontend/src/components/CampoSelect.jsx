import Form from 'react-bootstrap/Form';

/**
 * Lista desplegable con etiqueta y mensaje de error por campo. `opciones` es `[{ valor, etiqueta }]` (ver
 * `opcionesDe` en `config/catalogos.js`); `placeholder` agrega una primera opción vacía. `onCambiar` recibe el valor.
 */
export default function CampoSelect({
  id,
  etiqueta,
  valor,
  onCambiar,
  opciones,
  placeholder,
  error,
  ayuda,
  className = 'mb-3',
  ...control
}) {
  return (
    <Form.Group className={className} controlId={id}>
      <Form.Label>{etiqueta}</Form.Label>
      <Form.Select value={valor} onChange={(evento) => onCambiar(evento.target.value)} isInvalid={Boolean(error)} {...control}>
        {placeholder && <option value="">{placeholder}</option>}
        {opciones.map(({ valor: opcion, etiqueta: texto }) => (
          <option key={opcion} value={opcion}>{texto}</option>
        ))}
      </Form.Select>
      <Form.Control.Feedback type="invalid">{error}</Form.Control.Feedback>
      {ayuda && <Form.Text muted>{ayuda}</Form.Text>}
    </Form.Group>
  );
}
