import { validationResult } from 'express-validator';

const MENSAJE_POR_DEFECTO = 'Valor inválido.';

/**
 * Cierra la cadena de validadores de express-validator: responde 400 con un detalle por campo. Nunca devuelve el
 * valor recibido, para no reflejar en la respuesta lo que envió el cliente.
 */
export const validarCampos = (req, res, next) => {
  const resultado = validationResult(req);
  if (resultado.isEmpty()) return next();

  const detalles = resultado.array({ onlyFirstError: true }).map((error) => ({
    campo: error.path,
    mensaje: error.msg === 'Invalid value' ? MENSAJE_POR_DEFECTO : error.msg,
  }));
  return res.status(400).json({ error: true, mensaje: 'Datos inválidos.', detalles });
};
