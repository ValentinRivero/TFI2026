export const enteroPositivo = (campo) => ({
  validator: (valor) => valor === null || (Number.isInteger(valor) && valor > 0),
  message: `${campo} debe ser un número entero positivo.`,
});

/** Opciones compartidas por las colecciones: fechas con los nombres de Django y `id` en lugar de `_id` y `__v`. */
export const opcionesDeEsquema = (coleccion) => ({
  collection: coleccion,
  timestamps: { createdAt: 'fecha_creacion', updatedAt: 'fecha_modificacion' },
  toJSON: {
    virtuals: true,
    versionKey: false,
    transform: (documento, json) => {
      delete json._id;
      return json;
    },
  },
});
