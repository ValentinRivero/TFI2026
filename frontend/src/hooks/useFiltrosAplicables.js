import { useState } from 'react';

/**
 * Filtros con borrador: lo que se escribe no consulta hasta que se aplica (botón "Buscar" o Enter). Evita una petición
 * por cada tecla en los campos de texto y de números. `validar(borrador)` devuelve los errores por campo; mientras haya
 * alguno, el borrador no se aplica.
 *
 * Devuelve `borrador`, `aplicados` (los que usa la consulta), `errores`, `cambiar`, `aplicar(evento)` y `limpiar`.
 */
export default function useFiltrosAplicables(iniciales, validar = () => ({})) {
  const [borrador, setBorrador] = useState(iniciales);
  const [aplicados, setAplicados] = useState(iniciales);
  const [intentado, setIntentado] = useState(false);

  const errores = intentado ? validar(borrador) : {};

  const cambiar = (campo, valor) => setBorrador((actuales) => ({ ...actuales, [campo]: valor }));

  const aplicar = (evento) => {
    evento?.preventDefault();
    setIntentado(true);
    if (Object.keys(validar(borrador)).length > 0) return;
    setAplicados(borrador);
  };

  const limpiar = () => {
    setBorrador(iniciales);
    setAplicados(iniciales);
    setIntentado(false);
  };

  return { borrador, aplicados, errores, cambiar, aplicar, limpiar };
}
