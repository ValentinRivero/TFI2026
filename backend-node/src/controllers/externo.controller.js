import { matchedData } from 'express-validator';

import { ErrorHttp } from '../middlewares/errores.middleware.js';
import { obtenerComplejoPublico } from '../services/djangoClient.service.js';
import { obtenerPronostico } from '../services/openMeteo.service.js';
import { crearCacheTemporal } from '../utils/cacheTemporal.js';

// Open-Meteo actualiza el clima actual cada 15 minutos: antes no hay datos nuevos que pedir. La caché además evita
// que una ruta pública multiplique las consultas a Django y al proveedor.
export const cacheDeClima = crearCacheTemporal({ duracionMs: 15 * 60 * 1000, maximo: 500 });

// Open-Meteo publica sus datos con licencia CC BY 4.0: el frontend muestra la fuente junto al clima.
const FUENTE = 'Open-Meteo.com';

const consultarClima = async (complejoId) => {
  const complejo = await obtenerComplejoPublico(complejoId);
  if (!complejo) throw new ErrorHttp(404, 'No se encontró el complejo.');
  const clima = await obtenerPronostico(complejo);
  return { complejo: { id: complejo.id, nombre: complejo.nombre }, ...clima, fuente: FUENTE };
};

/**
 * Clima del complejo para su página pública. Se guarda la consulta en curso y no solo su resultado, así varios
 * pedidos simultáneos comparten una única llamada; si falla, o el complejo no existe, se descarta y el pedido
 * siguiente vuelve a intentar.
 */
export const obtenerClima = async (req, res) => {
  const { complejoId } = matchedData(req, { locations: ['params'] });

  let consulta = cacheDeClima.obtener(complejoId);
  if (!consulta) {
    consulta = consultarClima(complejoId);
    cacheDeClima.guardar(complejoId, consulta);
    consulta.catch(() => {
      if (cacheDeClima.obtener(complejoId) === consulta) cacheDeClima.borrar(complejoId);
    });
  }
  res.json(await consulta);
};
