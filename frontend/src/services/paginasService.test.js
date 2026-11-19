import { describe, expect, test, vi } from 'vitest';
import { traerTodasLasPaginas } from './paginasService.js';

const pagina = (results, next) => ({ results, next });

describe('traerTodasLasPaginas', () => {
  test('junta las páginas hasta que no hay siguiente', async () => {
    const pedir = vi.fn()
      .mockResolvedValueOnce(pagina([1, 2], 'http://x/?page=2'))
      .mockResolvedValueOnce(pagina([3], null));

    await expect(traerTodasLasPaginas(pedir)).resolves.toEqual([1, 2, 3]);
    expect(pedir).toHaveBeenNthCalledWith(1, 1);
    expect(pedir).toHaveBeenNthCalledWith(2, 2);
  });

  test('respeta el tope de páginas', async () => {
    const pedir = vi.fn().mockResolvedValue(pagina([1], 'siguiente'));

    await expect(traerTodasLasPaginas(pedir, 3)).resolves.toEqual([1, 1, 1]);
    expect(pedir).toHaveBeenCalledTimes(3);
  });

  test('una respuesta sin resultados no rompe', async () => {
    await expect(traerTodasLasPaginas(async () => null)).resolves.toEqual([]);
  });

  test('un error de una página se propaga', async () => {
    const pedir = vi.fn().mockResolvedValueOnce(pagina([1], 'x')).mockRejectedValueOnce(new Error('falla'));

    await expect(traerTodasLasPaginas(pedir)).rejects.toThrow('falla');
  });
});
