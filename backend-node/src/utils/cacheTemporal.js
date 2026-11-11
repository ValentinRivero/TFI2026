/**
 * Caché en memoria con vencimiento y tamaño máximo. Al llenarse descarta la entrada guardada hace más tiempo, así
 * pedidos con muchas claves distintas no hacen crecer la memoria del proceso sin límite.
 */
export const crearCacheTemporal = ({ duracionMs, maximo }) => {
  const entradas = new Map();

  return {
    obtener(clave) {
      const entrada = entradas.get(clave);
      if (!entrada) return undefined;
      if (Date.now() >= entrada.vence) {
        entradas.delete(clave);
        return undefined;
      }
      return entrada.valor;
    },
    guardar(clave, valor) {
      entradas.delete(clave);
      entradas.set(clave, { valor, vence: Date.now() + duracionMs });
      if (entradas.size > maximo) entradas.delete(entradas.keys().next().value);
    },
    borrar(clave) {
      entradas.delete(clave);
    },
    vaciar() {
      entradas.clear();
    },
  };
};
