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
