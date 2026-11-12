import { ErrorHttp, ErrorServicioExterno } from '../middlewares/errores.middleware.js';
import Evento from '../models/Evento.js';
import { obtenerComplejoPublico } from '../services/djangoClient.service.js';

/**
 * Registra una visita al complejo o una consulta de su grilla. Valida primero el evento (sin costo de red) y recién
 * después confirma con Django que el complejo esté habilitado. El usuario sale del token, nunca del cuerpo.
 */
export const registrarEvento = async (req, res) => {
  const evento = new Evento({
    tipo_evento: req.body.tipo_evento,
    complejo_id: req.body.complejo_id,
    metadata: req.body.metadata ?? {},
    usuario_id: req.usuario?.id ?? null,
  });
  await evento.validate();

  if (!(await obtenerComplejoPublico(evento.complejo_id))) {
    throw new ErrorHttp(404, 'No se encontró el complejo.');
  }
  try {
    await evento.save();
  } catch (error) {
    console.error('No se pudo guardar el evento en MongoDB:', error.message);
    throw new ErrorServicioExterno('MongoDB', error);
  }
  res.status(201).json({ id: evento.id });
};
