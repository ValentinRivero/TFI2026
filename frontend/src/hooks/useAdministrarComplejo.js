import { useNavigate } from 'react-router-dom';
import useComplejoActivo from './useComplejoActivo.js';

const RUTA_PANEL = '/panel';

/**
 * Lleva al superadmin al panel con un complejo ya seleccionado. Reutiliza el complejo activo del panel (`useComplejoActivo`,
 * el mismo estado que cambia el selector de `/panel`): se elige el complejo y se navega, y `LayoutPanel` lo resuelve
 * entre los que el usuario administra. `administrar(complejo)` recibe cualquier objeto con `id`.
 */
export default function useAdministrarComplejo() {
  const { elegir } = useComplejoActivo();
  const navegar = useNavigate();

  return (complejo) => {
    elegir(complejo.id);
    navegar(RUTA_PANEL);
  };
}
