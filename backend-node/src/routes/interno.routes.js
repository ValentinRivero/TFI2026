import { Router } from 'express';
import { body } from 'express-validator';

import { crearNotificacionInterna } from '../controllers/interno.controller.js';
import { crearLimitadorInterno } from '../middlewares/rateLimit.middleware.js';
import { autenticarServicio } from '../middlewares/servicioInterno.middleware.js';
import { validarCampos } from '../middlewares/validarCampos.middleware.js';
import { TIPOS_EVENTO } from '../models/Evento.js';
import { CATEGORIAS_NOTIFICACION, PRIORIDADES_NOTIFICACION } from '../models/Notificacion.js';

const ENTERO_POSITIVO = 'Debe ser un número entero positivo.';
const presente = (valor) => valor !== undefined && valor !== null;

const router = Router();

// Rutas que solo usa backend-django; nginx no las publica. La clave se verifica antes que el cuerpo, para no
// describirle a quien no la tiene qué campos se esperan.
router.use(crearLimitadorInterno(), autenticarServicio);

router.post(
  '/notificaciones',
  body('complejo_id').optional({ values: 'null' }).isInt({ min: 1 }).withMessage(ENTERO_POSITIVO).toInt(),
  body('complejo_id')
    .custom((complejo, { req }) => presente(complejo) || presente(req.body.usuario_id))
    .withMessage('Indicá un complejo o un usuario destinatario.').bail()
    .custom((complejo, { req }) => presente(complejo) || req.body.evento === undefined)
    .withMessage('Un evento necesita el complejo donde ocurrió.'),
  body('usuario_id').optional({ values: 'null' }).isInt({ min: 1 }).withMessage(ENTERO_POSITIVO).toInt(),
  body('categoria')
    .isInt().withMessage('Debe ser un número entero.').bail()
    .toInt()
    .isIn(Object.values(CATEGORIAS_NOTIFICACION)).withMessage('Categoría no admitida.'),
  body('prioridad')
    .optional()
    .isInt().withMessage('Debe ser un número entero.').bail()
    .toInt()
    .isIn(Object.values(PRIORIDADES_NOTIFICACION)).withMessage('Prioridad no admitida.'),
  body('mensaje')
    .isString().withMessage('Debe ser un texto.').bail()
    .trim()
    .notEmpty().withMessage('El mensaje es obligatorio.')
    .isLength({ max: 280 }).withMessage('El mensaje no puede superar los 280 caracteres.'),
  body('evento').optional().isObject({ strict: true }).withMessage('Debe ser un objeto.'),
  // Por esta vía solo llegan las reservas realizadas: las visitas y consultas las registra el frontend.
  body('evento.tipo_evento')
    .if(body('evento').isObject({ strict: true }))
    .isInt().withMessage('Debe ser un número entero.').bail()
    .toInt()
    .isIn([TIPOS_EVENTO.RESERVA_REALIZADA]).withMessage('Por esta vía solo se registran reservas realizadas (3).'),
  body('evento.usuario_id')
    .if(body('evento').isObject({ strict: true }))
    .optional({ values: 'null' })
    .isInt({ min: 1 }).withMessage(ENTERO_POSITIVO)
    .toInt(),
  validarCampos,
  crearNotificacionInterna,
);

export default router;
