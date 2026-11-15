const SIN_MOVIMIENTO = '(prefers-reduced-motion: reduce)';

/** Desplaza la página hasta un elemento; con "reducir movimiento" activado en el sistema el salto es directo. */
export const desplazarA = (elemento) => {
  if (!elemento) return;
  const reducido = typeof window.matchMedia === 'function' && window.matchMedia(SIN_MOVIMIENTO).matches;
  elemento.scrollIntoView({ behavior: reducido ? 'auto' : 'smooth', block: 'start' });
};
