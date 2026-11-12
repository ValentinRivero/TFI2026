import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { aParametrosUrl, leerFiltros } from '../utils/notificaciones.js';

/**
 * Filtros de una bandeja de notificaciones (`estado`, `prioridad`, `categoria`) guardados en la URL: el enlace se
 * puede compartir y cada cambio reemplaza la entrada del historial, para que "Atrás" vuelva a la pantalla anterior.
 */
export default function useFiltrosNotificaciones() {
  const [parametros, setParametros] = useSearchParams();
  const filtros = leerFiltros(parametros);
  const clave = parametros.toString();

  const cambiar = useCallback((campo, valor) => {
    setParametros(aParametrosUrl({ ...leerFiltros(new URLSearchParams(clave)), [campo]: valor }), { replace: true });
  }, [clave, setParametros]);

  const limpiar = useCallback(() => setParametros({}, { replace: true }), [setParametros]);

  const hayFiltros = Object.keys(aParametrosUrl(filtros)).length > 0;

  return { filtros, cambiar, limpiar, hayFiltros };
}
