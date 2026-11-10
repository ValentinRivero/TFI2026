import { Router } from 'express';
import { body, param, query } from 'express-validator';

import { registrarEvento } from '../controllers/actividad.controller.js';
import {
  cambiarEstadoDeNotificacion,
  listarActividad,
  listarMisNotificaciones,
  listarNotificacionesDelComplejo,
} from '../controllers/panel.controller.js';
import { autenticar, autenticarOpcional } from '../middlewares/auth.middleware.js';
import { crearLimitadorActividad } from '../middlewares/rateLimit.middleware.js';
import { permitirRoles, ROLES, ROLES_DE_COMPLEJO } from '../middlewares/rol.middleware.js';
import { validarCampos } from '../middlewares/validarCampos.middleware.js';
import { TIPOS_EVENTO } from '../models/Evento.js';
import { ESTADOS_NOTIFICACION } from '../models/Notificacion.js';
import { validarPaginacion } from '../utils/paginacion.js';

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

// El rol se controla antes de validar, para no confirmarle a un jugador qué parámetros espera el panel.
const soloPanel = [autenticar, permitirRoles(...ROLES_DE_COMPLEJO, ROLES.SUPERADMIN)];
const complejoPedido = query('complejo_id').isInt({ min: 1 }).withMessage('Debe ser un número entero positivo.').toInt();
const ESTADOS_EDITABLES = [ESTADOS_NOTIFICACION.NO_LEIDA, ESTADOS_NOTIFICACION.LEIDA];

router.get('/', ...soloPanel, complejoPedido, ...validarPaginacion, validarCampos, listarActividad);

router.get(
  '/notificaciones',
  ...soloPanel,
  complejoPedido,
  ...validarPaginacion,
  validarCampos,
  listarNotificacionesDelComplejo,
);

// Cualquier cuenta, con o sin rol activo, ve sus propias notificaciones.
router.get('/notificaciones/mias', autenticar, ...validarPaginacion, validarCampos, listarMisNotificaciones);

router.patch(
  '/notificaciones/:id',
  autenticar,
  param('id').isMongoId().withMessage('Identificador inválido.'),
  body('estado')
    .isInt().withMessage('Debe ser un número entero.').bail()
    .toInt()
    .isIn(ESTADOS_EDITABLES).withMessage('Solo se puede marcar como no leída (1) o leída (2).'),
  validarCampos,
  cambiarEstadoDeNotificacion,
);

export default router;
