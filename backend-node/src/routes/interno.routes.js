import { Router } from 'express';
import { body } from 'express-validator';

import { LIMITES } from '../config/parametros.js';
import { crearNotificacionInterna, obtenerEstadoInterno } from '../controllers/interno.controller.js';
import { crearLimitadorInterno } from '../middlewares/rateLimit.middleware.js';
import { autenticarServicio } from '../middlewares/servicioInterno.middleware.js';
import { validarCampos } from '../middlewares/validarCampos.middleware.js';
import { TIPOS_EVENTO } from '../models/Evento.js';
import { AMBITOS_NOTIFICACION, CATEGORIAS_NOTIFICACION, PRIORIDADES_NOTIFICACION } from '../models/Notificacion.js';

const ENTERO_POSITIVO = 'Debe ser un número entero positivo.';
const presente = (valor) => valor !== undefined && valor !== null;
const hayUsuarios = (lista) => Array.isArray(lista) && lista.length > 0;

const router = Router();

// Rutas que solo usa backend-django; nginx no las publica. La clave se verifica antes que el cuerpo, para no
// describirle a quien no la tiene qué campos se esperan.
router.use(crearLimitadorInterno(), autenticarServicio);

router.post(
  '/notificaciones',
  body('complejo_id').optional({ values: 'null' }).isInt({ min: 1 }).withMessage(ENTERO_POSITIVO).toInt(),
  body('complejo_id')
    .custom((complejo, { req }) => (
      presente(complejo) || presente(req.body.usuario_id) || hayUsuarios(req.body.usuarios_ids)
    ))
    .withMessage('Indicá un complejo o un usuario destinatario.').bail()
    .custom((complejo, { req }) => presente(complejo) || req.body.evento === undefined)
    .withMessage('Un evento necesita el complejo donde ocurrió.'),
  body('usuario_id').optional({ values: 'null' }).isInt({ min: 1 }).withMessage(ENTERO_POSITIVO).toInt(),
  body('usuario_id')
    .custom((usuario, { req }) => !presente(usuario) || !presente(req.body.usuarios_ids))
    .withMessage('Indicá un usuario o una lista de usuarios, no los dos.'),
  body('usuarios_ids')
    .optional({ values: 'null' })
    .isArray({ min: 1, max: LIMITES.maximoDestinatarios })
    .withMessage(`Debe ser una lista de 1 a ${LIMITES.maximoDestinatarios} usuarios.`),
  body('usuarios_ids.*').isInt({ min: 1 }).withMessage(ENTERO_POSITIVO).toInt(),
  // Entrada del registro del complejo, además de los avisos personales: texto propio (con los ids de lo ocurrido).
  body('registro').optional().isObject({ strict: true }).withMessage('Debe ser un objeto.'),
  body('registro')
    .custom((registro, { req }) => registro === undefined || presente(req.body.complejo_id))
    .withMessage('Una entrada del registro necesita el complejo.'),
  body('registro.ambito')
    .if(body('registro').isObject({ strict: true }))
    .isInt().withMessage('Debe ser un número entero.').bail()
    .toInt()
    .isIn(Object.values(AMBITOS_NOTIFICACION)).withMessage('Ámbito no admitido.'),
  body('registro.mensaje')
    .if(body('registro').isObject({ strict: true }))
    .isString().withMessage('Debe ser un texto.').bail()
    .trim()
    .notEmpty().withMessage('El mensaje es obligatorio.')
    .isLength({ max: LIMITES.maximoMensaje })
    .withMessage(`El mensaje no puede superar los ${LIMITES.maximoMensaje} caracteres.`),
  body('clave_unica')
    .optional({ values: 'null' })
    .isString().withMessage('Debe ser un texto.').bail()
    .trim()
    .isLength({ min: 1, max: LIMITES.maximoClaveUnica })
    .withMessage(`La clave debe tener entre 1 y ${LIMITES.maximoClaveUnica} caracteres.`),
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
    .isLength({ max: LIMITES.maximoMensaje })
    .withMessage(`El mensaje no puede superar los ${LIMITES.maximoMensaje} caracteres.`),
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

// Estado y carga del servicio, para el reporte que Django envía a los superadministradores.
router.get('/estado', obtenerEstadoInterno);

export default router;
