import Alerta from './Alerta.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Confirmación de una baja u otra acción que no se puede deshacer desde la pantalla. `mostrar` se deduce de `abierto`;
 * `error` es el `ErrorApi` del último intento y se muestra dentro del diálogo, que queda abierto para reintentar o
 * cancelar (por ejemplo, la baja de una cancha con ocupación futura).
 */
export default function ModalConfirmarAccion({ abierto, titulo, texto, error, textoConfirmar, onConfirmar, onCancelar }) {
  return (
    <ModalConfirmar
      mostrar={abierto}
      titulo={titulo}
      variante="danger"
      textoConfirmar={textoConfirmar}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
    >
      {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
      <p className="mb-0">{texto}</p>
    </ModalConfirmar>
  );
}
