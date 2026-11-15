/**
 * Lista de barras proporcionales hechas solo con CSS (sin librerías de gráficos). Cada fila lleva su etiqueta, su valor
 * en texto y un ancho entre 0 y 100; el valor en texto es lo que leen los lectores de pantalla, la barra es decorativa.
 * `filas`: `[{ clave, etiqueta, valor, ancho, variante? }]`, con `variante` `ok`, `aviso`, `peligro`, `info` o `neutro`
 * (ver las reglas `.barra-relleno-*` de `styles/tema.css`).
 */
export default function ListaBarras({ filas, etiqueta }) {
  return (
    <ul className="lista-barras list-unstyled mb-0" aria-label={etiqueta}>
      {filas.map(({ clave, etiqueta: texto, valor, ancho, variante = 'ok' }) => (
        <li key={clave} className="barra-fila">
          <div className="barra-fila-texto">
            <span>{texto}</span>
            <span className="num">{valor}</span>
          </div>
          <div className="barra" aria-hidden="true">
            <div className={`barra-relleno barra-relleno-${variante}`} style={{ width: `${ancho}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
