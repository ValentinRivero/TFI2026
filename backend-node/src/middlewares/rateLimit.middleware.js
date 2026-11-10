import { rateLimit } from 'express-rate-limit';

const MENSAJE_LIMITE = 'Superaste el límite de solicitudes. Intentá nuevamente más tarde.';

export const crearLimitador = ({ ventanaMs, maximo }) => rateLimit({
  windowMs: ventanaMs,
  limit: maximo,
  standardHeaders: 'draft-8',
  legacyHeaders: false,
  handler: (req, res) => {
    res.status(429).json({ error: true, mensaje: MENSAJE_LIMITE });
  },
});

export const crearLimitadorGlobal = () => crearLimitador({
  ventanaMs: Number(process.env.RATE_LIMIT_VENTANA_MS) || 60_000,
  maximo: Number(process.env.RATE_LIMIT_MAXIMO) || 120,
});

// Las rutas que escriben en la base sin exigir sesión tienen un cupo propio, menor que el global.
export const crearLimitadorActividad = () => crearLimitador({
  ventanaMs: Number(process.env.RATE_LIMIT_ACTIVIDAD_VENTANA_MS) || 60_000,
  maximo: Number(process.env.RATE_LIMIT_ACTIVIDAD_MAXIMO) || 30,
});
