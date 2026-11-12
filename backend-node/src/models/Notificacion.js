import mongoose from 'mongoose';

import bajaLogica from './bajaLogica.plugin.js';
import { enteroPositivo, opcionesDeEsquema } from './comunes.js';
import { ESTADOS_EVENTO } from './Evento.js';
import { TAMANO_DE_PAGINA } from '../utils/paginacion.js';

export const CATEGORIAS_NOTIFICACION = Object.freeze({ RESERVAS: 1, CUENTAS: 2, OPERATORIA: 3, SISTEMA: 4 });
export const PRIORIDADES_NOTIFICACION = Object.freeze({ NORMAL: 1, URGENTE: 2 });
export const ESTADOS_NOTIFICACION = Object.freeze({ BAJA: 0, NO_LEIDA: 1, LEIDA: 2 });

const MAXIMO_MENSAJE = 280;
// El mensaje se muestra en paneles compartidos por el personal del complejo: no lleva datos personales (Ley 25.326).
const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/;
// Del evento solo viaja lo que la bandeja muestra: `metadata` y `usuario_id` no llegan al panel.
const CAMPOS_DEL_EVENTO = 'tipo_evento complejo_id fecha_creacion';

const notificacionSchema = new mongoose.Schema(
  {
    evento: { type: mongoose.Schema.Types.ObjectId, ref: 'Evento', default: null },
    complejo_id: {
      type: Number,
      default: null,
      validate: [
        enteroPositivo('complejo_id'),
        {
          // Validador de campo y no hook `pre('validate')`: el error llega con su ruta, junto a los demás del documento.
          validator(valor) {
            return valor !== null || this.usuario_id !== null;
          },
          message: 'La notificación necesita un complejo o un usuario destinatario.',
        },
      ],
    },
    usuario_id: { type: Number, default: null, validate: enteroPositivo('usuario_id') },
    categoria: {
      type: Number,
      required: [true, 'La categoría es obligatoria.'],
      enum: { values: Object.values(CATEGORIAS_NOTIFICACION), message: 'Categoría no admitida.' },
    },
    prioridad: {
      type: Number,
      enum: { values: Object.values(PRIORIDADES_NOTIFICACION), message: 'Prioridad no admitida.' },
      default: PRIORIDADES_NOTIFICACION.NORMAL,
    },
    mensaje: {
      type: String,
      trim: true,
      required: [true, 'El mensaje es obligatorio.'],
      maxlength: [MAXIMO_MENSAJE, `El mensaje no puede superar los ${MAXIMO_MENSAJE} caracteres.`],
      validate: { validator: (valor) => !EMAIL.test(valor), message: 'El mensaje no puede incluir un email.' },
    },
    estado: {
      type: Number,
      enum: { values: Object.values(ESTADOS_NOTIFICACION), message: 'Estado no admitido.' },
      default: ESTADOS_NOTIFICACION.NO_LEIDA,
    },
  },
  opcionesDeEsquema('notificaciones'),
);

const VIGENTES = [ESTADOS_NOTIFICACION.NO_LEIDA, ESTADOS_NOTIFICACION.LEIDA];

/**
 * Filtro de la bandeja de un destinatario. La de un complejo trae solo sus avisos generales: los dirigidos a un
 * usuario puntual los ve únicamente ese usuario. Sin destinatario se rechaza, para no listar las de todos.
 */
notificacionSchema.statics.filtroDeBandeja = function filtroDeBandeja({ complejo_id: complejoId, usuario_id: usuarioId }) {
  if (!complejoId && !usuarioId) {
    throw new Error('La bandeja necesita un destinatario: complejo_id o usuario_id.');
  }
  return {
    ...(complejoId ? { complejo_id: complejoId } : {}),
    usuario_id: usuarioId ?? null,
    estado: { $in: VIGENTES },
  };
};

/**
 * Una página de la bandeja, de a 20 por defecto: de la más reciente a la más antigua, con el evento resuelto por
 * `populate` solo si sigue activo.
 */
notificacionSchema.statics.bandeja = function bandeja(destinatario, { salto = 0, limite = TAMANO_DE_PAGINA } = {}) {
  return this.find(this.filtroDeBandeja(destinatario))
    .sort({ fecha_creacion: -1 })
    .skip(salto)
    .limit(limite)
    .populate({ path: 'evento', select: CAMPOS_DEL_EVENTO, match: { estado: ESTADOS_EVENTO.ACTIVO } });
};

/** Una notificación vigente por id, con el mismo `populate` que la bandeja. */
notificacionSchema.statics.vigentePorId = function vigentePorId(id) {
  return this.findOne({ _id: id, estado: { $in: VIGENTES } })
    .populate({ path: 'evento', select: CAMPOS_DEL_EVENTO, match: { estado: ESTADOS_EVENTO.ACTIVO } });
};

notificacionSchema.index({ complejo_id: 1, estado: 1, fecha_creacion: -1 });
notificacionSchema.index({ usuario_id: 1, estado: 1, fecha_creacion: -1 });
notificacionSchema.plugin(bajaLogica);

export default mongoose.model('Notificacion', notificacionSchema);
