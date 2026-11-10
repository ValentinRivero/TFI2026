const OPERACIONES_DE_BORRADO = ['deleteOne', 'deleteMany', 'findOneAndDelete'];

const MENSAJE = 'Los documentos no se borran: se usa baja lógica (estado 0).';

/**
 * Aplica la regla de baja lógica del proyecto a un esquema: bloquea todo borrado físico, sea por consulta o sobre un
 * documento cargado, y agrega `darDeBaja()`. Exige que el esquema tenga un campo `estado` donde 0 es la baja.
 */
export default function bajaLogica(schema) {
  schema.pre(OPERACIONES_DE_BORRADO, { query: true, document: true }, () => {
    throw new Error(MENSAJE);
  });

  schema.methods.darDeBaja = function darDeBaja() {
    this.estado = 0;
    return this.save();
  };
}
