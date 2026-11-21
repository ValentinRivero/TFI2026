import { useEffect, useRef, useState } from 'react';
import { PARAMETROS } from '../config/parametros.js';
import { copiarAlPortapapeles } from '../utils/portapapeles.js';

const RESULTADO = Object.freeze({ NINGUNO: 'ninguno', COPIADO: 'copiado', FALLO: 'fallo' });

/**
 * Copia `texto` al portapapeles. `copiado` y `fallo` se encienden unos segundos para confirmar el resultado en el
 * botón y vuelven solos; el temporizador se limpia al desmontar.
 */
export default function useCopiar(texto) {
  const [resultado, setResultado] = useState(RESULTADO.NINGUNO);
  const temporizador = useRef(null);

  useEffect(() => () => clearTimeout(temporizador.current), []);

  const copiar = async () => {
    const copiado = await copiarAlPortapapeles(texto);
    setResultado(copiado ? RESULTADO.COPIADO : RESULTADO.FALLO);
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(
      () => setResultado(RESULTADO.NINGUNO),
      PARAMETROS.pagos.segundosCopiado * 1000,
    );
  };

  return { copiar, copiado: resultado === RESULTADO.COPIADO, fallo: resultado === RESULTADO.FALLO };
}
