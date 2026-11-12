import { rateLimit } from 'express-rate-limit';

const MENSAJE_LIMITE = 'Superaste el límite de solicitudes. Intentá nuevamente más tarde.';

export const crearLimitador = ({ ventanaMs, maximo, omitir }) => rateLimit({
  windowMs: ventanaMs,
  limit: maximo,
  skip: omitir,
  standardHeaders: 'draft-8',
  legacyHeaders: false,
  handler: (req, res) => {
    res.status(429).json({ error: true, mensaje: MENSAJE_LIMITE });
  },
});

// Las rutas internas llegan siempre desde la IP de backend-django: contarlas acá agotaría el cupo que esa IP
// comparte en el mismo contador, así que usan su propio limitador.
export const crearLimitadorGlobal = () => crearLimitador({
  ventanaMs: Number(process.env.RATE_LIMIT_VENTANA_MS) || 60_000,
  maximo: Number(process.env.RATE_LIMIT_MAXIMO) || 120,
  omitir: (req) => req.path.startsWith('/api/interno/'),
});

// Las rutas que escriben en la base sin exigir sesión tienen un cupo propio, menor que el global.
export const crearLimitadorActividad = () => crearLimitador({
  ventanaMs: Number(process.env.RATE_LIMIT_ACTIVIDAD_VENTANA_MS) || 60_000,
  maximo: Number(process.env.RATE_LIMIT_ACTIVIDAD_MAXIMO) || 30,
});

// Cupo de backend-django en las rutas internas: alcanza para picos de reservas y frena un bucle por error.
export const crearLimitadorInterno = () => crearLimitador({
  ventanaMs: Number(process.env.RATE_LIMIT_INTERNO_VENTANA_MS) || 60_000,
  maximo: Number(process.env.RATE_LIMIT_INTERNO_MAXIMO) || 600,
});
