import { useOutletContext } from 'react-router-dom';
import { puedeVer } from '../config/catalogos.js';
import useSesion from './useSesion.js';

/**
 * Contexto que `LayoutPanel` entrega a cada subvista de `/panel/*`: el `complejo` activo, `actualizarComplejo` para
 * reflejar un cambio guardado y `permisos`, que replica la matriz de roles (el control real lo hacen los backends).
 */
export default function useContextoPanel() {
  const { complejo, actualizarComplejo } = useOutletContext();
  const { rol } = useSesion();
  return {
    complejo,
    actualizarComplejo,
    permisos: {
      configurar: puedeVer('configurarComplejo', rol),
      operadores: puedeVer('operadoresComplejo', rol),
      canchas: puedeVer('administrarCanchas', rol),
      excepciones: puedeVer('excepciones', rol),
    },
  };
}
