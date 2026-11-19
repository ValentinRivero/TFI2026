import { useEffect, useState } from 'react';
import { PARAMETROS } from '../config/parametros.js';

/** Devuelve `valor` recién después de que deja de cambiar durante `demoraMs`: así una búsqueda no consulta por cada tecla. */
export default function useValorConDemora(valor, demoraMs = PARAMETROS.catalogo.busquedaDemoraMs) {
  const [demorado, setDemorado] = useState(valor);

  useEffect(() => {
    const espera = setTimeout(() => setDemorado(valor), demoraMs);
    return () => clearTimeout(espera);
  }, [valor, demoraMs]);

  return demorado;
}
