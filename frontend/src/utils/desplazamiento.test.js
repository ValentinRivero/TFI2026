import { afterEach, describe, expect, test, vi } from 'vitest';
import { desplazarA } from './desplazamiento.js';

const elemento = () => ({ scrollIntoView: vi.fn() });

const simularVentana = (reducido) => vi.stubGlobal('window', { matchMedia: () => ({ matches: reducido }) });

describe('desplazarA', () => {
  afterEach(() => vi.unstubAllGlobals());

  test('sin elemento no hace nada', () => {
    simularVentana(false);
    expect(() => desplazarA(null)).not.toThrow();
  });

  test('se desplaza suavemente hasta el inicio del elemento', () => {
    simularVentana(false);
    const destino = elemento();

    desplazarA(destino);

    expect(destino.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
  });

  test('con reducir movimiento activado salta sin animación', () => {
    simularVentana(true);
    const destino = elemento();

    desplazarA(destino);

    expect(destino.scrollIntoView).toHaveBeenCalledWith({ behavior: 'auto', block: 'start' });
  });

  test('si el navegador no ofrece matchMedia usa el desplazamiento suave', () => {
    vi.stubGlobal('window', {});
    const destino = elemento();

    desplazarA(destino);

    expect(destino.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
  });
});
