import 'dotenv/config';

import app from './app.js';
import { conectarDB } from './src/config/db.js';

const puerto = Number(process.env.PORT) || 3000;

try {
  await conectarDB();
} catch {
  // conectarDB ya registró la causa sin credenciales: sin base no se atienden pedidos a medias.
  process.exit(1);
}

app.listen(puerto, () => {
  console.log(`backend-node escuchando en el puerto ${puerto}`);
});
