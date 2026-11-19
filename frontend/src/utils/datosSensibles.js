const MARCAS_DE_AUSENCIA = new Set(['-', '—', '–']);

/**
 * Un valor se puede ocultar solo si trae un dato real. Vacío, `null`, `undefined` o un guion (la ausencia que
 * muestran las tablas, como una IP ya anonimizada por retención) no ocultan nada y se muestran como texto.
 */
export const esValorEnmascarable = (valor) => {
  if (valor === null || valor === undefined) return false;
  const texto = String(valor).trim();
  return texto !== '' && !MARCAS_DE_AUSENCIA.has(texto);
};
