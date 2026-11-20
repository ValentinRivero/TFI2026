import { useState } from 'react';
import { esValorEnmascarable } from '../utils/datosSensibles.js';
import Icono from './Icono.jsx';

/**
 * Dato sensible (por ejemplo, la IP de un evento de auditoría) oculto por defecto tras una máscara de ancho fijo,
 * con un botón de ojo para mostrarlo u ocultarlo. Cada instancia guarda su propia visibilidad: se monta una por
 * registro (con `key` por id), así que al paginar o filtrar vuelve a quedar oculto. Un valor ausente se muestra como
 * texto común, sin botón. `mascara`, `etiquetaMostrar` y `etiquetaOcultar` vienen de `i18n/es.js`.
 */
export default function ValorOculto({ valor, ausente = '-', mascara, etiquetaMostrar, etiquetaOcultar }) {
  const [visible, setVisible] = useState(false);

  if (!esValorEnmascarable(valor)) return <span>{ausente}</span>;

  const etiqueta = visible ? etiquetaOcultar : etiquetaMostrar;

  return (
    <span className="valor-oculto">
      <span className="valor-oculto-texto">{visible ? valor : mascara}</span>
      <button
        type="button"
        className="valor-oculto-boton"
        aria-label={etiqueta}
        aria-pressed={visible}
        title={etiqueta}
        onClick={() => setVisible((actual) => !actual)}
      >
        <Icono nombre={visible ? 'ojoTachado' : 'ojo'} tamano={18} />
      </button>
    </span>
  );
}
