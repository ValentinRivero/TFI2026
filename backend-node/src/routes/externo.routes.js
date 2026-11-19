import { Router } from 'express';
import { param } from 'express-validator';

import { obtenerClima } from '../controllers/externo.controller.js';
import { validarCampos } from '../middlewares/validarCampos.middleware.js';

const router = Router();

// Pública, como el detalle del complejo: el clima no depende de quién lo pide y no se reenvía ningún token.
router.get(
  '/clima/:complejoId',
  param('complejoId').isInt({ min: 1 }).withMessage('Debe ser un número entero positivo.').toInt(),
  validarCampos,
  obtenerClima,
);

export default router;
