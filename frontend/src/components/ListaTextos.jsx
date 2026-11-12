import { t, tLista } from '../i18n/index.js';

/** Lista con viñetas cuyos ítems son las entradas `clave.0`, `clave.1`... del diccionario de textos. */
export default function ListaTextos({ clave, params }) {
  const cantidad = tLista(clave).length;
  return (
    <ul>
      {Array.from({ length: cantidad }, (_, indice) => (
        <li key={indice}>{t(`${clave}.${indice}`, params)}</li>
      ))}
    </ul>
  );
}
