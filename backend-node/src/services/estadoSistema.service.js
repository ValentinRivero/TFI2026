import mongoose from 'mongoose';

import { obtenerParametros } from '../config/parametros.js';
import Evento, { ESTADOS_EVENTO } from '../models/Evento.js';
import Notificacion, { ESTADOS_NOTIFICACION } from '../models/Notificacion.js';
import { contarFallasExternas } from '../utils/fallasExternas.js';

const BYTES_POR_MB = 1024 * 1024;
const MS_POR_DIA = 24 * 60 * 60 * 1000;
const CONECTADO = 1;

const aMb = (bytes) => Math.round(bytes / BYTES_POR_MB);

/** Latencia de un ping a MongoDB en milisegundos, o `null` si no hay conexión o no respondió. */
const medirMongo = async () => {
  if (mongoose.connection.readyState !== CONECTADO) return null;
  const inicio = performance.now();
  try {
    await mongoose.connection.db.admin().ping();
  } catch {
    return null;
  }
  return Math.round(performance.now() - inicio);
};

// Los operadores `$gte` los arma el servidor: `sanitizeFilter` (config/db.js) los anularía sin la marca de confianza.
export const desdeHace24Horas = (ahora) => mongoose.trusted({ $gte: new Date(ahora - MS_POR_DIA) });

export const filtroDeEventosRecientes = (ahora) => ({
  estado: ESTADOS_EVENTO.ACTIVO,
  fecha_creacion: desdeHace24Horas(ahora),
});

const contarActividad = async (ahora) => {
  try {
    const [eventos, sinLeer] = await Promise.all([
      Evento.countDocuments(filtroDeEventosRecientes(ahora)),
      Notificacion.countDocuments({ estado: ESTADOS_NOTIFICACION.NO_LEIDA }),
    ]);
    return { eventos, sinLeer };
  } catch {
    return { eventos: null, sinLeer: null };
  }
};

/**
 * Estado y carga de backend-node para backend-django: memoria, latencia de MongoDB, actividad de las últimas 24 horas y
 * fallas recientes de servicios externos. Informa `degradado` con los motivos cuando algo supera los umbrales. No lleva
 * datos personales: son conteos y tiempos. Quien conoce a los superadministradores es Django, que emite el aviso.
 */
export const medirEstado = async (ahora = Date.now()) => {
  const umbrales = obtenerParametros().estado;
  const latenciaMongo = await medirMongo();
  const actividad = latenciaMongo === null ? { eventos: null, sinLeer: null } : await contarActividad(ahora);
  const memoria = process.memoryUsage();
  const fallas = contarFallasExternas(umbrales.ventanaFallasMs, ahora);

  const motivos = [];
  if (latenciaMongo === null) motivos.push('MongoDB no responde');
  else if (latenciaMongo > umbrales.latenciaMongoMaximaMs) {
    motivos.push(`MongoDB tarda ${latenciaMongo} ms (máximo ${umbrales.latenciaMongoMaximaMs} ms)`);
  }
  if (aMb(memoria.rss) > umbrales.memoriaMaximaMb) {
    motivos.push(`memoria de ${aMb(memoria.rss)} MB (máximo ${umbrales.memoriaMaximaMb} MB)`);
  }
  if (fallas >= umbrales.fallasExternasMaximas) {
    motivos.push(`${fallas} fallas de servicios externos en ${Math.round(umbrales.ventanaFallasMs / 60_000)} min`);
  }

  return {
    estado: motivos.length === 0 ? 'ok' : 'degradado',
    motivos,
    metricas: {
      memoria_rss_mb: aMb(memoria.rss),
      memoria_heap_mb: aMb(memoria.heapUsed),
      latencia_mongo_ms: latenciaMongo,
      eventos_24h: actividad.eventos,
      notificaciones_sin_leer: actividad.sinLeer,
      fallas_externas_recientes: fallas,
      uptime_s: Math.round(process.uptime()),
    },
  };
};
