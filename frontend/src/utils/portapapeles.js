/** Respaldo para navegadores o contextos sin `navigator.clipboard` (HTTP, WebViews): copia seleccionando un campo oculto. */
const copiarConSeleccion = (texto, documento) => {
  if (!documento?.body || typeof documento.execCommand !== 'function') return false;
  const campo = documento.createElement('textarea');
  campo.value = texto;
  campo.setAttribute('readonly', '');
  campo.setAttribute('aria-hidden', 'true');
  campo.style.position = 'fixed';
  campo.style.opacity = '0';
  documento.body.appendChild(campo);
  campo.select();
  try {
    return documento.execCommand('copy');
  } catch {
    return false;
  } finally {
    documento.body.removeChild(campo);
  }
};

/**
 * Copia `texto` al portapapeles y responde si pudo. Usa `navigator.clipboard` (solo en contextos seguros) y, si falta
 * o lo rechaza, el respaldo con selección. `entorno` permite probarlo sin navegador. Nunca lanza.
 */
export const copiarAlPortapapeles = async (texto, entorno = globalThis) => {
  const portapapeles = entorno.navigator?.clipboard;
  if (portapapeles?.writeText) {
    try {
      await portapapeles.writeText(texto);
      return true;
    } catch {
      // Permiso denegado o contexto no seguro: se intenta el respaldo.
    }
  }
  return copiarConSeleccion(texto, entorno.document);
};
