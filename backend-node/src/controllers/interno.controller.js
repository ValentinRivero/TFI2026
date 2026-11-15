import { matchedData } from 'express-validator';

import Evento from '../models/Evento.js';
import Notificacion from '../models/Notificacion.js';
import { medirEstado } from '../services/estadoSistema.service.js';
import { enMongo } from '../utils/mongo.js';

const CLAVE_DUPLICADA = 11000;

// `null` es el aviso general de un complejo, sin usuario destinatario. Con una entrada de registro, el general lo
// aporta ella y no se crea otro.
const destinatariosDe = ({ usuarios_ids: usuariosIds, usuario_id: usuarioId }, hayRegistro) => {
  if (usuariosIds) return [...new Set(usuariosIds)];
  if (usuarioId !== undefined && usuarioId !== null) return [usuarioId];
  return hayRegistro ? [] : [null];
};

/**
 * Guarda el aviso. Si ese usuario ya tiene uno con la misma `clave_unica`, el índice único lo rechaza y se lo descarta:
 * es la deduplicación de los recordatorios y los reportes repetidos. Devuelve si se creó.
 */
const guardarSinRepetir = (notificacion) => enMongo(async () => {
  try {
    await notificacion.save();
    return true;
  } catch (error) {
    if (error?.code === CLAVE_DUPLICADA) return false;
    throw error;
  }
});

/**
 * Aviso emitido por backend-django para un complejo, un usuario o varios usuarios a la vez (cada uno recibe el suyo en
 * su bandeja personal). Si trae el evento que lo originó (una reserva realizada), se registra primero el evento una
 * sola vez y los avisos quedan vinculados a él. Todos los documentos se validan antes de guardar cualquiera, así un
 * error de datos no deja un evento suelto. Si MongoDB falla entre un `save()` y otro, lo ya guardado queda: el evento
 * es un hecho que ocurrió y el reporte de actividad lo cuenta igual. Con `clave_unica`, un aviso repetido para el mismo
 * usuario se ignora y se informa en `omitidas`; si no se crea ninguno responde 200 en lugar de 201. Con `registro`
 * se guarda además, sin destinatario, la entrada del registro del complejo (la ven los tres roles de complejo, sin
 * estado de lectura), con su propio mensaje y su ámbito operativo o comercial.
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
  // Como con `evento`, `matchedData` arma `registro` aunque no haya llegado: se mira el cuerpo.
  const hayRegistro = req.body.registro !== undefined;
  const notificaciones = destinatariosDe(datos, hayRegistro).map((usuarioId) => new Notificacion({
    evento: evento?._id ?? null,
    complejo_id: datos.complejo_id ?? null,
    usuario_id: usuarioId,
    categoria: datos.categoria,
    prioridad: datos.prioridad,
    mensaje: datos.mensaje,
    clave_unica: datos.clave_unica ?? null,
  }));

  const registro = hayRegistro ? new Notificacion({
    evento: evento?._id ?? null,
    complejo_id: datos.complejo_id,
    usuario_id: null,
    categoria: datos.categoria,
    prioridad: datos.prioridad,
    mensaje: datos.registro.mensaje,
    ambito: datos.registro.ambito,
  }) : null;

  await evento?.validate();
  await Promise.all([...notificaciones, ...(registro ? [registro] : [])].map((documento) => documento.validate()));
  if (evento) await enMongo(() => evento.save());
  if (registro) await enMongo(() => registro.save());

  const creadas = [];
  for (const notificacion of notificaciones) {
    if (await guardarSinRepetir(notificacion)) creadas.push(notificacion);
  }

  res.status(creadas.length > 0 || registro ? 201 : 200).json({
    id: creadas[0]?.id ?? null,
    ids: creadas.map((notificacion) => notificacion.id),
    evento: evento?.id ?? null,
    registro: registro?.id ?? null,
    omitidas: notificaciones.length - creadas.length,
  });
};

/** Estado y carga de este servicio para el reporte que Django envía a los superadministradores. */
export const obtenerEstadoInterno = async (req, res) => {
  res.json(await medirEstado());
};
