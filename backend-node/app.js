import cors from 'cors';
import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';

import { crearOpcionesCors } from './src/config/cors.js';
import { obtenerParametros } from './src/config/parametros.js';
import { manejarErrores, rutaNoEncontrada } from './src/middlewares/errores.middleware.js';
import { crearLimitadorGlobal } from './src/middlewares/rateLimit.middleware.js';
import actividadRoutes from './src/routes/actividad.routes.js';
import externoRoutes from './src/routes/externo.routes.js';
import internoRoutes from './src/routes/interno.routes.js';
import reporteAuxRoutes from './src/routes/reporteAux.routes.js';
import saludRoutes from './src/routes/salud.routes.js';

const { numProxies, bodyMaximoBytes } = obtenerParametros();

const app = express();

// Saltos de proxy de confianza (nginx): sin esto, el limitador vería a todos los clientes con la IP del proxy.
app.set('trust proxy', numProxies);

app.use(helmet());
app.use(cors(crearOpcionesCors()));
if (process.env.NODE_ENV !== 'test') {
  app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));
}
app.use(crearLimitadorGlobal());
// Los eventos y notificaciones son livianos: un cuerpo mayor es un error del cliente o un intento de abuso.
app.use(express.json({ limit: bodyMaximoBytes }));

app.use('/api/salud', saludRoutes);
app.use('/api/actividad', actividadRoutes);
app.use('/api/reportes-aux', reporteAuxRoutes);
app.use('/api/externa', externoRoutes);
app.use('/api/interno', internoRoutes);

app.use(rutaNoEncontrada);
app.use(manejarErrores);

export default app;
