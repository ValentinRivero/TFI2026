import AlertaReintento from './AlertaReintento.jsx';
import Cargando from './Cargando.jsx';
import EstadoVacio from './EstadoVacio.jsx';
import Paginador from './Paginador.jsx';
import TablaApilable from './TablaApilable.jsx';

/**
 * Colección paginada de un panel con todos sus estados: carga, error con reintento, vacío y tabla con el `Paginador`
 * arriba y abajo. `lista` es lo que devuelve `useListaPaginada`; `renderFila(item)` devuelve la fila (`<tr>`).
 * `resumen` es el texto de cantidad total y `vacio` los textos (y acciones) del estado sin elementos.
 */
export default function ListaAdmin({ lista, columnas, etiqueta, resumen, vacio, errorTitulo, renderFila }) {
  const { items, paginas, pagina, irAPagina, cargando, error, recargar } = lista;

  if (cargando) return <Cargando variante="seccion" />;
  if (error) return <AlertaReintento titulo={errorTitulo} mensaje={error.mensaje} onReintentar={recargar} />;
  if (items.length === 0) {
    return <EstadoVacio titulo={vacio.titulo} descripcion={vacio.descripcion}>{vacio.children}</EstadoVacio>;
  }

  return (
    <section aria-label={etiqueta}>
      <p className="small text-secondary" role="status">{resumen}</p>
      <Paginador pagina={pagina} total={paginas} onCambiar={irAPagina} alineacion="izquierda" className="mb-2" />
      <TablaApilable columnas={columnas} etiqueta={etiqueta}>{items.map(renderFila)}</TablaApilable>
      <Paginador pagina={pagina} total={paginas} onCambiar={irAPagina} alineacion="izquierda" className="mt-2" />
    </section>
  );
}
