import { useLocation, useNavigate } from 'react-router-dom';

/**
 * Aviso que otra pantalla dejó al navegar (`navigate(ruta, { state: { aviso } })`), por ejemplo la baja de la cuenta.
 * `descartar` lo quita de la entrada del historial para que no reaparezca al recargar.
 */
export default function useAvisoDeNavegacion() {
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const aviso = typeof ubicacion.state?.aviso === 'string' ? ubicacion.state.aviso : null;

  return {
    aviso,
    descartar: () => navegar(`${ubicacion.pathname}${ubicacion.search}`, { replace: true, state: null }),
  };
}
