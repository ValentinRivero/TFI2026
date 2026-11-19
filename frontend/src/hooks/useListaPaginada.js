import { useState } from 'react';
import { totalDePaginas } from '../utils/paginacion.js';
import useConsulta from './useConsulta.js';

/**
 * Lista paginada con numeración (`Paginador`): pide una sola página por vez. Al cambiar las dependencias (filtros)
 * vuelve a la primera. Si la página pedida dejó de existir (por ejemplo, tras dar de baja el último elemento de la
 * última página) cae a la primera en lugar de mostrar un error.
 *
 * `pedirPagina(numero, signal)` devuelve `{ count, results }`. Devuelve `items`, `total`, `paginas`, `pagina`,
 * `irAPagina`, `cargando`, `error` y `recargar`.
 */
export default function useListaPaginada(pedirPagina, dependencias = []) {
  const clave = JSON.stringify(dependencias);
  const [seleccion, setSeleccion] = useState({ clave, pagina: 1 });
  const pagina = seleccion.clave === clave ? seleccion.pagina : 1;

  const consulta = useConsulta(async (signal) => {
    try {
      return { ...(await pedirPagina(pagina, signal)), pagina };
    } catch (error) {
      if (error?.status === 404 && pagina > 1) return { ...(await pedirPagina(1, signal)), pagina: 1 };
      throw error;
    }
  }, [...dependencias, pagina]);

  const { datos, cargando } = consulta;

  return {
    items: datos?.results ?? [],
    total: datos?.count ?? 0,
    paginas: totalDePaginas(datos?.count ?? 0),
    pagina: cargando ? pagina : (datos?.pagina ?? pagina),
    irAPagina: (numero) => setSeleccion({ clave, pagina: numero }),
    cargando,
    error: consulta.error,
    recargar: consulta.recargar,
  };
}
