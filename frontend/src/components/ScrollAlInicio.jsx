import { useEffect, useRef } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

/**
 * Lleva la página al tope al navegar a otra pantalla, como lo haría una carga completa. Solo reacciona al cambio de
 * ruta (`pathname`): los filtros y las pestañas que cambian la query no mueven el desplazamiento, y volver atrás
 * (`POP`) se deja al navegador. No dibuja nada.
 */
export default function ScrollAlInicio() {
  const { pathname } = useLocation();
  const tipo = useNavigationType();
  const anterior = useRef(pathname);

  useEffect(() => {
    if (anterior.current === pathname) return;
    anterior.current = pathname;
    if (tipo !== 'POP') window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname, tipo]);

  return null;
}
