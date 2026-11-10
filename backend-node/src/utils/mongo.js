import { ErrorServicioExterno } from '../middlewares/errores.middleware.js';

/** Ejecuta una operación de MongoDB y convierte su falla en un 502, con la causa solo en el log. */
export const enMongo = async (operacion) => {
  try {
    return await operacion();
  } catch (error) {
    console.error('MongoDB no respondió como se esperaba:', error.message);
    throw new ErrorServicioExterno('MongoDB', error);
  }
};
