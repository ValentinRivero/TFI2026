import { Router } from 'express';
import { body, param } from 'express-validator';

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
import {
  CATEGORIAS_NOTIFICACION,
  ESTADOS_NOTIFICACION,
  PRIORIDADES_NOTIFICACION,
} from '../models/Notificacion.js';
import { validarPaginacion } from '../utils/paginacion.js';
import { complejoEnConsulta, parametroUnico } from '../utils/validaciones.js';

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
const ESTADOS_EDITABLES = [ESTADOS_NOTIFICACION.NO_LEIDA, ESTADOS_NOTIFICACION.LEIDA];

const filtroNumerico = (campo, valores, mensaje) => parametroUnico(campo)
  .optional()
  .isInt().withMessage('Debe ser un número entero.').bail()
  .toInt()
  .isIn(valores)
  .withMessage(mensaje);

// Las dadas de baja nunca se listan: el filtro de estado admite solo los dos vigentes.
const filtrosDeNotificaciones = [
  filtroNumerico('categoria', Object.values(CATEGORIAS_NOTIFICACION), 'Categoría no admitida.'),
  filtroNumerico('prioridad', Object.values(PRIORIDADES_NOTIFICACION), 'Prioridad no admitida.'),
  filtroNumerico('estado', ESTADOS_EDITABLES, 'Solo se filtra por no leída (1) o leída (2).'),
];

router.get('/', ...soloPanel, complejoEnConsulta(), ...validarPaginacion, validarCampos, listarActividad);

router.get(
  '/notificaciones',
  ...soloPanel,
  complejoEnConsulta(),
  ...validarPaginacion,
  ...filtrosDeNotificaciones,
  validarCampos,
  listarNotificacionesDelComplejo,
);

// Cualquier cuenta, con o sin rol activo, ve sus propias notificaciones.
router.get(
  '/notificaciones/mias',
  autenticar,
  ...validarPaginacion,
  ...filtrosDeNotificaciones,
  validarCampos,
  listarMisNotificaciones,
);

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
