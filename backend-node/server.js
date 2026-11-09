import 'dotenv/config';

import app from './app.js';

const puerto = Number(process.env.PORT) || 3000;

app.listen(puerto, () => {
  console.log(`backend-node escuchando en el puerto ${puerto}`);
});
