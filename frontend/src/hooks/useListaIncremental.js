import { useCallback, useEffect, useRef, useState } from 'react';
import useConsulta from './useConsulta.js';

const SIN_EXTRA = Object.freeze({ base: null, items: [], paginas: 1, siguiente: null });

/**
 * Lista paginada que crece con un botón "Mostrar más": pide la primera página al montar y cada vez que cambian las
 * dependencias (filtros), y agrega las siguientes de a una, sin descargar la colección completa.
 *
 * `pedirPagina(numero, signal)` devuelve `{ count, next, results }`. Devuelve:
 * `items`, `total`, `hayMas`, `cargando` (primera página), `cargandoMas`, `error` (de la primera página),
 * `errorMas` (de una página siguiente: la lista ya cargada se conserva), `cargarMas` y `recargar`.
 */
export default function useListaIncremental(pedirPagina, dependencias = []) {
  const primera = useConsulta((signal) => pedirPagina(1, signal), dependencias);
  const [extra, setExtra] = useState(SIN_EXTRA);
  const [mas, setMas] = useState({ base: null, cargando: false, error: null });
  const ultimaFuncion = useRef(pedirPagina);
  const controlador = useRef(null);

  useEffect(() => {
    ultimaFuncion.current = pedirPagina;
  });

  const base = primera.datos;

  // Una página siguiente en vuelo pertenece a la primera página que la originó: si esa cambia, se descarta.
  useEffect(() => () => controlador.current?.abort(), [base]);

  // Las páginas agregadas valen solo mientras la primera página sea la misma que las originó.
  const agregadas = extra.base === base ? extra : SIN_EXTRA;
  const siguiente = base === null ? null : (agregadas.base === null ? base.next : agregadas.siguiente);

  const cargarMas = useCallback(async () => {
    if (base === null || !siguiente) return;
    const pagina = agregadas.paginas + 1;
    controlador.current?.abort();
    const actual = new AbortController();
    controlador.current = actual;
    setMas({ base, cargando: true, error: null });
    try {
      const datos = await ultimaFuncion.current(pagina, actual.signal);
      if (actual.signal.aborted) return;
      setExtra((previo) => {
        const vigente = previo.base === base ? previo : { base, items: [], paginas: 1, siguiente: null };
        return { base, items: [...vigente.items, ...datos.results], paginas: pagina, siguiente: datos.next };
      });
      setMas({ base, cargando: false, error: null });
    } catch (error) {
      if (actual.signal.aborted) return;
      setMas({ base, cargando: false, error });
    }
  }, [base, siguiente, agregadas.paginas]);

  const estadoMas = mas.base === base ? mas : { cargando: false, error: null };

  return {
    items: [...(base?.results ?? []), ...agregadas.items],
    total: base?.count ?? 0,
    hayMas: Boolean(siguiente),
    cargando: primera.cargando,
    cargandoMas: estadoMas.cargando,
    error: primera.error,
    errorMas: estadoMas.error,
    cargarMas,
    recargar: primera.recargar,
  };
}
