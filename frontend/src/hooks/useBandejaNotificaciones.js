import { useState } from 'react';
import { FILTRO_ESTADO_NOTIFICACION } from '../config/catalogos.js';
import { aplicarLeidas } from '../utils/notificaciones.js';
import useListaIncremental from './useListaIncremental.js';

/**
 * Bandeja de notificaciones que crece con "Mostrar más" (ver `useListaIncremental`) y refleja de inmediato las que se
 * marcan como leídas, sin volver a pedir la lista: `registrarLeida(id)` las pasa a leídas o, si la bandeja muestra
 * solo no leídas, las oculta. En ese caso, si quedan páginas por traer, se vuelve a pedir la primera: al desaparecer
 * filas del servidor las páginas siguientes se corren y se saltearían avisos. Una notificación que esta bandeja no
 * tiene cargada se ignora.
 *
 * `filtros` son los de la URL (ver `utils/notificaciones.js`) y `pedirPagina(filtros, pagina, signal)` hace la consulta.
 */
export default function useBandejaNotificaciones(pedirPagina, filtros, dependencias = []) {
  const soloNoLeidas = filtros.estado === FILTRO_ESTADO_NOTIFICACION.NO_LEIDAS.valor;
  const clave = JSON.stringify([filtros, dependencias]);

  const lista = useListaIncremental((pagina, signal) => pedirPagina(filtros, pagina, signal), [filtros, ...dependencias]);
  const [marcadas, setMarcadas] = useState({ clave, ids: [] });

  // Las marcas valen solo para los filtros con los que se hicieron.
  const ids = marcadas.clave === clave ? marcadas.ids : [];
  const items = aplicarLeidas(lista.items, ids, soloNoLeidas);

  const registrarLeida = (id) => {
    if (!lista.items.some((item) => item.id === id)) return;
    setMarcadas((previas) => ({ clave, ids: [...(previas.clave === clave ? previas.ids : []), id] }));
    if (soloNoLeidas && lista.hayMas) lista.recargar();
  };

  return {
    ...lista,
    items,
    total: Math.max(0, lista.total - (lista.items.length - items.length)),
    registrarLeida,
  };
}
