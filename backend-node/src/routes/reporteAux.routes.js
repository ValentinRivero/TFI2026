import { Router } from 'express';
import { query } from 'express-validator';

import { obtenerVisitas } from '../controllers/reporteAux.controller.js';
import { autenticar } from '../middlewares/auth.middleware.js';
import { permitirRoles, ROLES, ROLES_DE_COMPLEJO } from '../middlewares/rol.middleware.js';
import { validarCampos } from '../middlewares/validarCampos.middleware.js';
import { diasEntre, esFecha } from '../utils/fechas.js';
import { complejoEnConsulta } from '../utils/validaciones.js';

// Mismo tope y mismos mensajes que el dashboard de Django, que muestra estas métricas junto a las de reservas.
const MAXIMO_DIAS = 366;
const FORMATO = 'Usá el formato AAAA-MM-DD.';

const router = Router();

router.get(
  '/visitas',
  autenticar,
  permitirRoles(...ROLES_DE_COMPLEJO, ROLES.SUPERADMIN),
  complejoEnConsulta(),
  query('fecha_desde').custom(esFecha).withMessage(FORMATO),
  query('fecha_hasta')
    .custom(esFecha).withMessage(FORMATO).bail()
    // Si `fecha_desde` es inválida ya tiene su propio error: no se compara contra ella.
    .custom((hasta, { req }) => !esFecha(req.query.fecha_desde) || hasta >= req.query.fecha_desde)
    .withMessage('Debe ser igual o posterior a fecha_desde.').bail()
    .custom((hasta, { req }) => !esFecha(req.query.fecha_desde) || diasEntre(req.query.fecha_desde, hasta) <= MAXIMO_DIAS)
    .withMessage(`El rango del reporte abarca como máximo ${MAXIMO_DIAS} días.`),
  validarCampos,
  obtenerVisitas,
);

export default router;
