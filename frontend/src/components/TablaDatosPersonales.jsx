import { tLista } from '../i18n/index.js';

/** Tabla de datos personales que trata el sistema, con su ubicación, finalidad y quién los ve. */
export default function TablaDatosPersonales() {
  return (
    <div className="table-responsive superficie">
      <table className="table mb-0 align-top">
        <thead>
          <tr>
            {tLista('privacidad.datos.columnas').map((columna) => <th key={columna}>{columna}</th>)}
          </tr>
        </thead>
        <tbody>
          {tLista('privacidad.datos.filas').map((fila) => (
            <tr key={fila[0]}>
              {fila.map((celda) => <td key={celda}>{celda}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
