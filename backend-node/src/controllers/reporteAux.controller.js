import { matchedData } from 'express-validator';

import Evento, { TIPOS_EVENTO } from '../models/Evento.js';
import { verificarAccesoAComplejo } from '../services/djangoClient.service.js';
import { diasDelRango } from '../utils/fechas.js';
import { enMongo } from '../utils/mongo.js';

const METRICAS = { [TIPOS_EVENTO.COMPLEJO_VISTO]: 'visitas', [TIPOS_EVENTO.GRILLA_CONSULTADA]: 'consultas_grilla' };

/**
 * Visitas al perfil y consultas de la grilla de un complejo, por día y en total, para el dashboard. Los días sin
 * actividad aparecen en cero, así el gráfico no tiene huecos.
 */
export const obtenerVisitas = async (req, res) => {
  const { complejo_id: complejoId, fecha_desde: desde, fecha_hasta: hasta } = matchedData(req, { locations: ['query'] });
  await verificarAccesoAComplejo(complejoId, req.token);

  const grupos = await enMongo(() => Evento.contarPorDia({
    complejoId, tipos: Object.keys(METRICAS).map(Number), desde, hasta,
  }));

  const porDia = new Map(diasDelRango(desde, hasta).map((fecha) => [fecha, { fecha, visitas: 0, consultas_grilla: 0 }]));
  const totales = { visitas: 0, consultas_grilla: 0 };
  grupos.forEach(({ _id: { fecha, tipo }, cantidad }) => {
    const metrica = METRICAS[tipo];
    const dia = porDia.get(fecha);
    if (!metrica || !dia) return;
    dia[metrica] += cantidad;
    totales[metrica] += cantidad;
  });

  res.json({
    filtros: { complejo_id: complejoId, fecha_desde: desde, fecha_hasta: hasta },
    totales,
    por_dia: [...porDia.values()],
  });
};
