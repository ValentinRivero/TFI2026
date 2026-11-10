import { query } from 'express-validator';

/**
 * Parámetro de consulta con un único valor. Repetido (`?complejo_id=4&complejo_id=5`) Express lo entrega como lista
 * y express-validator valida cada elemento por separado, así que la lista pasaría las reglas de un número.
 */
export const parametroUnico = (campo) => query(campo).not().isArray().withMessage('Enviá un solo valor.').bail();

export const complejoEnConsulta = () => parametroUnico('complejo_id')
  .isInt({ min: 1 }).withMessage('Debe ser un número entero positivo.')
  .toInt();
