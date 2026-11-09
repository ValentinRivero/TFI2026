import express from 'express';

import { manejarErrores, rutaNoEncontrada } from './src/middlewares/errores.middleware.js';
import saludRoutes from './src/routes/salud.routes.js';

const app = express();

// Los eventos y notificaciones son livianos: un cuerpo mayor es un error del cliente o un intento de abuso.
app.use(express.json({ limit: '10kb' }));

app.use('/api/salud', saludRoutes);

app.use(rutaNoEncontrada);
app.use(manejarErrores);

export default app;
