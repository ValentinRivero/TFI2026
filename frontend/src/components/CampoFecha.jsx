import { useRef, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import InputGroup from 'react-bootstrap/InputGroup';
import { t } from '../i18n/index.js';
import { aFechaVisible, desdeFechaVisible, enmascararFecha } from '../utils/formatos.js';
import Icono from './Icono.jsx';

/**
 * Campo de fecha que se ve siempre como `dd/mm/aaaa`, sin importar el idioma del navegador (el `<input type="date">`
 * nativo muestra `mm/dd/yyyy` en inglés). Se puede escribir con máscara o elegir en el calendario nativo, que se abre
 * desde el botón con `showPicker()`; el selector nativo queda oculto y solo aporta el calendario.
 *
 * `valor` y `onCambiar` usan `AAAA-MM-DD`, el formato de la API: `onCambiar` recibe una fecha completa y real, o
 * `''` mientras lo escrito está incompleto o no existe (así los formularios la tratan como faltante). Al salir del
 * campo, lo que no es una fecha válida se descarta.
 */
export default function CampoFecha({
  id,
  etiqueta,
  etiquetaOculta = false,
  valor,
  onCambiar,
  error,
  ayuda,
  min,
  max,
  disabled = false,
  className = 'mb-3',
  ...resto
}) {
  const nativo = useRef(null);
  const [escrito, setEscrito] = useState(null);

  // Mientras se escribe se muestra lo tipeado; si no, la fecha del valor.
  const visible = escrito ?? aFechaVisible(valor);

  const escribir = (evento) => {
    const texto = enmascararFecha(evento.target.value);
    setEscrito(texto);
    onCambiar(desdeFechaVisible(texto) ?? '');
  };

  const abrirCalendario = () => {
    const control = nativo.current;
    if (!control) return;
    if (typeof control.showPicker === 'function') control.showPicker();
    else control.focus();
  };

  return (
    <Form.Group className={className} controlId={id}>
      <Form.Label className={etiquetaOculta ? 'visually-hidden' : undefined}>{etiqueta}</Form.Label>
      <InputGroup hasValidation className="campo-fecha">
        <Form.Control
          type="text"
          inputMode="numeric"
          autoComplete="off"
          placeholder={t('comun.formatoFecha')}
          maxLength={10}
          className="num"
          value={visible}
          onChange={escribir}
          onBlur={() => setEscrito(null)}
          isInvalid={Boolean(error)}
          disabled={disabled}
          {...resto}
        />
        <Button
          variant="outline-secondary"
          aria-label={t('comun.abrirCalendario')}
          disabled={disabled}
          onClick={abrirCalendario}
        >
          <Icono nombre="calendario" tamano={18} />
        </Button>
        <input
          ref={nativo}
          type="date"
          className="campo-fecha-nativo"
          tabIndex={-1}
          aria-hidden="true"
          value={valor || ''}
          min={min}
          max={max}
          onChange={(evento) => {
            setEscrito(null);
            onCambiar(evento.target.value);
          }}
        />
        <Form.Control.Feedback type="invalid">{error}</Form.Control.Feedback>
      </InputGroup>
      {ayuda && <Form.Text muted>{ayuda}</Form.Text>}
    </Form.Group>
  );
}
