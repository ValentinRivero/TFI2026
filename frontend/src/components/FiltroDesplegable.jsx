import { useId } from 'react';
import Dropdown from 'react-bootstrap/Dropdown';
import Form from 'react-bootstrap/Form';

/**
 * Base visual de los filtros desplegables del catálogo: etiqueta, botón con el valor actual y menú flotante. El
 * contenido del menú (`children`) y el `pie` fijo lo aportan `FiltroSelect` y `FiltroServicios`. `className` va
 * en el contenedor, para que el menú tenga exactamente el ancho del botón y no el de la columna con su separación.
 */
export default function FiltroDesplegable({ etiqueta, textoBoton, children, pie = null, cerrarAlElegir = false, className = '' }) {
  const id = useId();

  return (
    <div className={className}>
      <Dropdown autoClose={cerrarAlElegir ? true : 'outside'}>
        <Form.Label id={`${id}-etiqueta`}>{etiqueta}</Form.Label>
        <Dropdown.Toggle
          id={`${id}-boton`}
          variant="outline-secondary"
          className="filtro-boton w-100 d-flex justify-content-between align-items-center text-start"
          aria-labelledby={`${id}-etiqueta ${id}-boton`}
        >
          <span className="text-truncate">{textoBoton}</span>
        </Dropdown.Toggle>

        <Dropdown.Menu className="filtro-menu w-100">
          <div className="filtro-lista">{children}</div>
          {pie && <div className="filtro-pie">{pie}</div>}
        </Dropdown.Menu>
      </Dropdown>
    </div>
  );
}
