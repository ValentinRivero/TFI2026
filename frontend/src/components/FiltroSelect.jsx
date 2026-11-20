import Dropdown from 'react-bootstrap/Dropdown';
import Icono from './Icono.jsx';
import FiltroDesplegable from './FiltroDesplegable.jsx';

/**
 * Filtro desplegable de elección única, con el mismo aspecto que el de servicios. `opciones` es una lista de
 * `{ valor, etiqueta }` (el valor es texto) y `onCambiar(valor)` avisa la elegida; el menú se cierra al elegir.
 */
export default function FiltroSelect({ etiqueta, opciones, valor, onCambiar, className = '' }) {
  const elegida = opciones.find((opcion) => opcion.valor === valor) ?? opciones[0];

  return (
    <FiltroDesplegable etiqueta={etiqueta} textoBoton={elegida.etiqueta} cerrarAlElegir className={className}>
      {opciones.map((opcion) => {
        const activa = opcion.valor === elegida.valor;
        return (
          <Dropdown.Item
            key={opcion.valor}
            as="button"
            type="button"
            className="filtro-opcion"
            active={activa}
            onClick={() => onCambiar(opcion.valor)}
          >
            <span className="flex-grow-1">{opcion.etiqueta}</span>
            {activa && <Icono nombre="check" tamano={16} />}
          </Dropdown.Item>
        );
      })}
    </FiltroDesplegable>
  );
}
