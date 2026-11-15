import { useCallback, useState } from 'react';

/**
 * Filtros que se aplican apenas cambian (selectores y fechas). `cambiar(campo, valor)` actualiza uno, `combinar(cambios)`
 * actualiza varios a la vez (una sola consulta) y `limpiar` vuelve a los valores iniciales.
 */
export default function useFiltros(iniciales) {
  const [filtros, setFiltros] = useState(iniciales);

  const cambiar = useCallback((campo, valor) => {
    setFiltros((actuales) => ({ ...actuales, [campo]: valor }));
  }, []);

  const combinar = useCallback((cambios) => {
    setFiltros((actuales) => ({ ...actuales, ...cambios }));
  }, []);

  return { filtros, cambiar, combinar, limpiar: () => setFiltros(iniciales) };
}
