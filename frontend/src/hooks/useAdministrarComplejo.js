import { useNavigate } from 'react-router-dom';
import { RUTAS_PANEL } from '../config/catalogos.js';
import useComplejoActivo from './useComplejoActivo.js';

/**
 * Lleva al superadmin al panel con un complejo ya seleccionado. Reutiliza el complejo activo del panel (`useComplejoActivo`,
 * el mismo estado que cambia el selector de `/panel`): se elige el complejo y se navega, y `LayoutPanel` lo resuelve
 * entre los que el usuario administra. `administrar(complejo, ruta)` recibe cualquier objeto con `id` y, opcionalmente,
 * la sección del panel (por defecto la configuración; ver `RUTAS_PANEL`).
 */
export default function useAdministrarComplejo() {
  const { elegir } = useComplejoActivo();
  const navegar = useNavigate();

  return (complejo, ruta = RUTAS_PANEL.configuracion) => {
    elegir(complejo.id);
    navegar(ruta);
  };
}
