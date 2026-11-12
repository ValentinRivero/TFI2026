import mongoose from 'mongoose';

import bajaLogica from './bajaLogica.plugin.js';
import { enteroPositivo, opcionesDeEsquema } from './comunes.js';
import { LIMITES } from '../config/parametros.js';
import { inicioDelDia, sumarDias, ZONA_HORARIA } from '../utils/fechas.js';

export const TIPOS_EVENTO = Object.freeze({ COMPLEJO_VISTO: 1, GRILLA_CONSULTADA: 2, RESERVA_REALIZADA: 3 });
export const ESTADOS_EVENTO = Object.freeze({ BAJA: 0, ACTIVO: 1 });

const MAXIMO_BYTES_METADATA = LIMITES.maximoBytesMetadata;

const esObjetoPlano = (valor) => valor !== null && typeof valor === 'object' && !Array.isArray(valor);

// Claves con `$` o `.` se interpretan como operadores o rutas de MongoDB: no pueden venir del cliente.
const tieneClavesInseguras = (valor) => {
  if (Array.isArray(valor)) return valor.some(tieneClavesInseguras);
  if (!esObjetoPlano(valor)) return false;
  return Object.entries(valor).some(
    ([clave, interno]) => clave.startsWith('$') || clave.includes('.') || tieneClavesInseguras(interno),
  );
};

const eventoSchema = new mongoose.Schema(
  {
    tipo_evento: {
      type: Number,
      required: [true, 'El tipo de evento es obligatorio.'],
      enum: { values: Object.values(TIPOS_EVENTO), message: 'Tipo de evento no admitido.' },
    },
    complejo_id: {
      type: Number,
      required: [true, 'El complejo es obligatorio.'],
      validate: enteroPositivo('complejo_id'),
    },
    usuario_id: { type: Number, default: null, validate: enteroPositivo('usuario_id') },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
      default: () => ({}),
      validate: [
        { validator: esObjetoPlano, message: 'metadata debe ser un objeto.' },
        { validator: (valor) => !tieneClavesInseguras(valor), message: 'metadata contiene claves no permitidas.' },
        {
          validator: (valor) => Buffer.byteLength(JSON.stringify(valor)) <= MAXIMO_BYTES_METADATA,
          message: `metadata no puede superar los ${MAXIMO_BYTES_METADATA} bytes.`,
        },
      ],
    },
    estado: {
      type: Number,
      enum: { values: Object.values(ESTADOS_EVENTO), message: 'Estado no admitido.' },
      default: ESTADOS_EVENTO.ACTIVO,
    },
  },
  { ...opcionesDeEsquema('eventos'), minimize: false },
);

/**
 * Cantidad de eventos activos de los tipos pedidos, por día de Argentina y por tipo, entre dos fechas `AAAA-MM-DD`
 * incluidas. Solo devuelve totales: `usuario_id` no sale de la base. Usa el índice del complejo por fecha.
 */
eventoSchema.statics.contarPorDia = function contarPorDia({ complejoId, tipos, desde, hasta }) {
  return this.aggregate([
    {
      $match: {
        complejo_id: complejoId,
        estado: ESTADOS_EVENTO.ACTIVO,
        tipo_evento: { $in: tipos },
        fecha_creacion: { $gte: inicioDelDia(desde), $lt: inicioDelDia(sumarDias(hasta, 1)) },
      },
    },
    {
      $group: {
        _id: {
          fecha: { $dateToString: { format: '%Y-%m-%d', date: '$fecha_creacion', timezone: ZONA_HORARIA } },
          tipo: '$tipo_evento',
        },
        cantidad: { $sum: 1 },
      },
    },
  ]);
};

eventoSchema.index({ complejo_id: 1, estado: 1, fecha_creacion: -1 });
eventoSchema.plugin(bajaLogica);

export default mongoose.model('Evento', eventoSchema);
