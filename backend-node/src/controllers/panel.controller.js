import { matchedData } from 'express-validator';

import { ErrorHttp } from '../middlewares/errores.middleware.js';
import { ROLES, ROLES_DE_COMPLEJO } from '../middlewares/rol.middleware.js';
import Evento, { ESTADOS_EVENTO } from '../models/Evento.js';
import Notificacion from '../models/Notificacion.js';
import { verificarAccesoAComplejo } from '../services/djangoClient.service.js';
import { enMongo } from '../utils/mongo.js';
import { paginar } from '../utils/paginacion.js';

const ROLES_DEL_PANEL = new Set([...ROLES_DE_COMPLEJO, ROLES.SUPERADMIN]);
const NO_ENCONTRADA = 'No se encontró la notificación.';

// El panel lo ve todo el personal del complejo: el usuario que generó el evento no se expone.
const serializarEvento = (evento) => ({
  id: evento.id,
  tipo_evento: evento.tipo_evento,
  complejo_id: evento.complejo_id,
  metadata: evento.metadata,
  fecha_creacion: evento.fecha_creacion ?? null,
});

const serializarNotificacion = (notificacion) => {
  const { evento } = notificacion;
  return {
    id: notificacion.id,
    complejo_id: notificacion.complejo_id,
    categoria: notificacion.categoria,
    prioridad: notificacion.prioridad,
    mensaje: notificacion.mensaje,
    estado: notificacion.estado,
    // Sin `populate`, o con el evento dado de baja, no hay nada que mostrar.
    evento: evento?.tipo_evento === undefined ? null : {
      id: evento.id,
      tipo_evento: evento.tipo_evento,
      complejo_id: evento.complejo_id,
      fecha_creacion: evento.fecha_creacion ?? null,
    },
    fecha_creacion: notificacion.fecha_creacion ?? null,
  };
};

const rutaDe = (req) => req.originalUrl.split('?')[0];

const listarPaginado = async (req, res, { modelo, filtro, filtrosDeEnlace, listar, serializar }) => {
  const { page: pagina, limit: limite } = matchedData(req, { locations: ['query'] });
  const total = await enMongo(() => modelo.countDocuments(filtro));
  const { salto, limite: tamano, encabezado } = paginar({
    ruta: rutaDe(req), filtros: filtrosDeEnlace, pagina, limite, total,
  });
  const resultados = await enMongo(() => listar({ salto, limite: tamano }));
  res.json({ ...encabezado, results: resultados.map(serializar) });
};

/** Actividad registrada de un complejo que el usuario administra, de la más reciente a la más antigua. */
export const listarActividad = async (req, res) => {
  const { complejo_id: complejoId } = matchedData(req, { locations: ['query'] });
  await verificarAccesoAComplejo(complejoId, req.token);
  const filtro = { complejo_id: complejoId, estado: ESTADOS_EVENTO.ACTIVO };
  await listarPaginado(req, res, {
    modelo: Evento,
    filtro,
    filtrosDeEnlace: { complejo_id: complejoId },
    listar: ({ salto, limite }) => Evento.find(filtro).sort({ fecha_creacion: -1 }).skip(salto).limit(limite),
    serializar: serializarEvento,
  });
};

/** Bandeja de avisos generales de un complejo que el usuario administra. */
export const listarNotificacionesDelComplejo = async (req, res) => {
  const { complejo_id: complejoId } = matchedData(req, { locations: ['query'] });
  await verificarAccesoAComplejo(complejoId, req.token);
  const destinatario = { complejo_id: complejoId };
  await listarPaginado(req, res, {
    modelo: Notificacion,
    filtro: Notificacion.filtroDeBandeja(destinatario),
    filtrosDeEnlace: destinatario,
    listar: (pagina) => Notificacion.bandeja(destinatario, pagina),
    serializar: serializarNotificacion,
  });
};

/** Bandeja propia de cualquier usuario autenticado: el destinatario sale siempre del token. */
export const listarMisNotificaciones = async (req, res) => {
  const destinatario = { usuario_id: req.usuario.id };
  await listarPaginado(req, res, {
    modelo: Notificacion,
    filtro: Notificacion.filtroDeBandeja(destinatario),
    filtrosDeEnlace: {},
    listar: (pagina) => Notificacion.bandeja(destinatario, pagina),
    serializar: serializarNotificacion,
  });
};

/**
 * Una notificación personal la modifica solo su titular; un aviso general, el personal con acceso al complejo,
 * confirmado en Django. En cualquier otro caso se responde 404, igual que si no existiera.
 */
const confirmarQuePuedeModificarla = async (notificacion, req) => {
  if (notificacion.usuario_id !== null) {
    if (notificacion.usuario_id !== req.usuario.id) throw new ErrorHttp(404, NO_ENCONTRADA);
    return;
  }
  if (!ROLES_DEL_PANEL.has(req.usuario.rol)) throw new ErrorHttp(404, NO_ENCONTRADA);
  try {
    await verificarAccesoAComplejo(notificacion.complejo_id, req.token);
  } catch (error) {
    if (error instanceof ErrorHttp && [403, 404].includes(error.status)) throw new ErrorHttp(404, NO_ENCONTRADA);
    throw error;
  }
};

/** Marca una notificación como leída o no leída. La baja no se hace por esta vía. */
export const cambiarEstadoDeNotificacion = async (req, res) => {
  const { id } = matchedData(req, { locations: ['params'] });
  const { estado } = matchedData(req, { locations: ['body'] });
  const notificacion = await enMongo(() => Notificacion.vigentePorId(id));
  if (!notificacion) throw new ErrorHttp(404, NO_ENCONTRADA);
  await confirmarQuePuedeModificarla(notificacion, req);

  notificacion.estado = estado;
  await enMongo(() => notificacion.save());
  res.json(serializarNotificacion(notificacion));
};
