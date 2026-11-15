import { useCallback, useState } from 'react';

/**
 * Filtros que se aplican apenas cambian (selectores y fechas). `cambiar(campo, valor)` actualiza uno y `limpiar`
 * vuelve a los valores iniciales.
 */
export default function useFiltros(iniciales) {
  const [filtros, setFiltros] = useState(iniciales);

  const cambiar = useCallback((campo, valor) => {
    setFiltros((actuales) => ({ ...actuales, [campo]: valor }));
  }, []);

  return { filtros, cambiar, limpiar: () => setFiltros(iniciales) };
}
