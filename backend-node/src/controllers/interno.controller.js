import { matchedData } from 'express-validator';

import Evento from '../models/Evento.js';
import Notificacion from '../models/Notificacion.js';
import { enMongo } from '../utils/mongo.js';

/**
 * Aviso emitido por backend-django para un complejo o un usuario. Si trae el evento que lo originó (una reserva
 * realizada), se registra primero el evento y el aviso queda vinculado a él. Los dos documentos se validan antes de
 * guardar cualquiera, así un error de datos no deja un evento suelto. Si MongoDB falla entre los dos `save()`, el
 * evento queda registrado sin aviso: es un hecho que ocurrió y el reporte de actividad lo cuenta igual.
 */
export const crearNotificacionInterna = async (req, res) => {
  const datos = matchedData(req, { locations: ['body'] });

  // Se mira el cuerpo y no `matchedData`, que arma `evento` aunque no haya llegado por tener reglas sobre sus campos.
  const evento = req.body.evento === undefined ? null : new Evento({
    tipo_evento: datos.evento.tipo_evento,
    complejo_id: datos.complejo_id,
    usuario_id: datos.evento.usuario_id ?? null,
    metadata: req.body.evento.metadata ?? {},
  });
  const notificacion = new Notificacion({
    evento: evento?._id ?? null,
    complejo_id: datos.complejo_id ?? null,
    usuario_id: datos.usuario_id ?? null,
    categoria: datos.categoria,
    prioridad: datos.prioridad,
    mensaje: datos.mensaje,
  });

  await evento?.validate();
  await notificacion.validate();
  if (evento) await enMongo(() => evento.save());
  await enMongo(() => notificacion.save());

  res.status(201).json({ id: notificacion.id, evento: evento?.id ?? null });
};
