import { createHash, timingSafeEqual } from 'node:crypto';

import { LIMITES } from '../config/parametros.js';
import { ErrorHttp } from './errores.middleware.js';

const LARGO_MINIMO_DE_CLAVE = LIMITES.largoMinimoClaveInterna;

// Se comparan los resúmenes y no las claves: tienen siempre el mismo largo, así `timingSafeEqual` no falla ni
// revela por el tiempo de respuesta cuántos caracteres coinciden o cuán larga es la clave.
const resumen = (texto) => createHash('sha256').update(texto).digest();

/**
 * Autentica a backend-django en las rutas internas con la clave compartida por variable de entorno. La clave viaja
 * en un encabezado propio que CORS no autoriza, así que ningún navegador puede enviarla. Sin una clave configurada
 * de largo suficiente la ruta queda cerrada para todos.
 */
export const autenticarServicio = (req, res, next) => {
  const configurada = process.env.INTERNAL_API_KEY;
  if (!configurada || configurada.length < LARGO_MINIMO_DE_CLAVE) {
    console.error(
      `INTERNAL_API_KEY no está configurada o tiene menos de ${LARGO_MINIMO_DE_CLAVE} caracteres: `
      + 'las rutas internas rechazan todo pedido.',
    );
    return next(new ErrorHttp(500, 'Error interno del servidor.'));
  }

  const recibida = req.get('X-Internal-Key');
  if (typeof recibida !== 'string' || !timingSafeEqual(resumen(recibida), resumen(configurada))) {
    console.warn(`Pedido a una ruta interna rechazado: clave ausente o inválida (IP ${req.ip}).`);
    return next(new ErrorHttp(401, 'Credenciales de servicio inválidas.'));
  }
  return next();
};
