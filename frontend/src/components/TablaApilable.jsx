/**
 * Tabla de administración. A partir de `lg` es una tabla densa; en pantallas chicas cada fila pasa a ser un bloque
 * apilado en el que cada celda muestra su etiqueta (`data-etiqueta`, que las filas toman de `columnas`). Las filas
 * son `children` y usan `CeldaTabla` para heredar esa etiqueta.
 *
 * `columnas`: `[{ clave, etiqueta, className? }]`. `etiqueta` rotula la tabla para lectores de pantalla.
 */
export default function TablaApilable({ columnas, etiqueta, children }) {
  return (
    <div className="superficie p-2">
      <div className="table-responsive">
        <table className="table table-hover align-middle mb-0 tabla-apilable" aria-label={etiqueta}>
          <thead>
            <tr>
              {columnas.map(({ clave, etiqueta: texto, className }) => (
                <th key={clave} scope="col" className={className}>{texto}</th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
    </div>
  );
}

/** Celda de una fila de `TablaApilable`: `etiqueta` es la de su columna, que se ve en la vista apilada. */
export function CeldaTabla({ etiqueta, className = '', children }) {
  return <td data-etiqueta={etiqueta} className={className}>{children}</td>;
}
