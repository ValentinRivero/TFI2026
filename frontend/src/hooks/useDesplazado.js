import { useEffect, useState } from 'react';

/**
 * Indica si la página se desplazó respecto del tope (`window.scrollY` mayor al `margen` en píxeles). La barra superior
 * lo usa para volverse levemente translúcida cuando no está arriba de todo.
 */
export default function useDesplazado(margen = 0) {
  const [desplazado, setDesplazado] = useState(() => typeof window !== 'undefined' && window.scrollY > margen);

  useEffect(() => {
    const actualizar = () => setDesplazado(window.scrollY > margen);
    window.addEventListener('scroll', actualizar, { passive: true });
    return () => window.removeEventListener('scroll', actualizar);
  }, [margen]);

  return desplazado;
}
