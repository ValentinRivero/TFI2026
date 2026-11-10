import { Router } from 'express';
import { body } from 'express-validator';

import { registrarEvento } from '../controllers/actividad.controller.js';
import { autenticarOpcional } from '../middlewares/auth.middleware.js';
import { crearLimitadorActividad } from '../middlewares/rateLimit.middleware.js';
import { validarCampos } from '../middlewares/validarCampos.middleware.js';
import { TIPOS_EVENTO } from '../models/Evento.js';

// "Reserva realizada" no se acepta acá: lo emite Django al confirmar una reserva real (punto 5.7). Una ruta pública
// que lo aceptara permitiría inundar a un complejo con avisos de reservas inexistentes.
const TIPOS_PUBLICOS = [TIPOS_EVENTO.COMPLEJO_VISTO, TIPOS_EVENTO.GRILLA_CONSULTADA];

const router = Router();

router.post(
  '/',
  crearLimitadorActividad(),
  autenticarOpcional,
  body('tipo_evento')
    .isInt().withMessage('Debe ser un número entero.').bail()
    .toInt()
    .isIn(TIPOS_PUBLICOS).withMessage('Solo se registran visitas al complejo (1) y consultas de la grilla (2).'),
  body('complejo_id').isInt({ min: 1 }).withMessage('Debe ser un número entero positivo.').toInt(),
  validarCampos,
  registrarEvento,
);

export default router;
