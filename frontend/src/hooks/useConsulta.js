import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

/**
 * Ejecuta una petición al montar y cada vez que cambian las dependencias. La petición anterior se cancela con un
 * `AbortController` (se pasa `signal` a la función), así una respuesta lenta nunca pisa a una más nueva: por
 * ejemplo, al cambiar rápido la fecha de la grilla.
 *
 * Devuelve `{ datos, error, cargando, recargar }`. Mientras `cargando` es verdadero, `datos` conserva el último
 * resultado, para que la pantalla decida si lo muestra o lo reemplaza por `Cargando`.
 */
export default function useConsulta(funcion, dependencias = []) {
  const [version, setVersion] = useState(0);
  const [resultado, setResultado] = useState({ consulta: null, datos: null, error: null });
  const ultimaFuncion = useRef(funcion);

  useEffect(() => {
    ultimaFuncion.current = funcion;
  });

  // Una consulta nueva por cada cambio de dependencias: `cargando` se deduce de ella, sin estado intermedio.
  // Las dependencias son valores simples (ids, fechas en texto, filtros): se comparan por su contenido serializado.
  const clave = JSON.stringify(dependencias);
  const consulta = useMemo(() => Symbol(`${clave}#${version}`), [clave, version]);

  useEffect(() => {
    const controlador = new AbortController();
    Promise.resolve()
      .then(() => ultimaFuncion.current(controlador.signal))
      .then(
        (datos) => {
          if (!controlador.signal.aborted) setResultado({ consulta, datos, error: null });
        },
        (error) => {
          if (!controlador.signal.aborted) setResultado((anterior) => ({ consulta, datos: anterior.datos, error }));
        },
      );
    return () => controlador.abort();
  }, [consulta]);

  const recargar = useCallback(() => setVersion((actual) => actual + 1), []);
  const cargando = resultado.consulta !== consulta;

  return {
    datos: resultado.datos,
    error: cargando ? null : resultado.error,
    cargando,
    recargar,
  };
}
