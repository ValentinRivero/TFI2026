import 'dotenv/config';

import app from './app.js';
import { conectarDB } from './src/config/db.js';
import { obtenerParametros } from './src/config/parametros.js';

const { puerto } = obtenerParametros();

try {
  await conectarDB();
} catch {
  // conectarDB ya registró la causa sin credenciales: sin base no se atienden pedidos a medias.
  process.exit(1);
}

app.listen(puerto, () => {
  console.log(`backend-node escuchando en el puerto ${puerto}`);
});
