import mongoose from 'mongoose';

import { obtenerParametros } from './parametros.js';

// Un filtro armado con datos del cliente ({ "$ne": "" }) se trata como valor literal y no como operador.
mongoose.set('sanitizeFilter', true);

const ocultarCredenciales = (texto) => String(texto).replace(/\/\/[^@/\s]+@/g, '//***@');

let vigilandoConexion = false;

const vigilarConexion = () => {
  if (vigilandoConexion) return;
  vigilandoConexion = true;
  mongoose.connection.on('disconnected', () => console.error('MongoDB desconectado.'));
  mongoose.connection.on('error', (error) => console.error('Error de MongoDB:', ocultarCredenciales(error.message)));
};

export const conectarDB = async () => {
  try {
    const uri = process.env.MONGO_URI;
    if (!uri) throw new Error('MONGO_URI no está configurada.');
    const { timeoutSeleccionMs, maxPoolSize } = obtenerParametros().mongo;
    await mongoose.connect(uri, { serverSelectionTimeoutMS: timeoutSeleccionMs, maxPoolSize });
  } catch (error) {
    console.error('No se pudo conectar a MongoDB:', ocultarCredenciales(error.message));
    throw error;
  }
  vigilarConexion();
  console.log('MongoDB conectado.');
};
