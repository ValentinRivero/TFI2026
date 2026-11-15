import { describe, expect, test } from 'vitest';
import { totalDePaginas, ventanaDePaginas } from './paginacion.js';

describe('ventanaDePaginas', () => {
  test.each([
    [1, 1, [1]],
    [1, 2, [1, 2]],
    [2, 2, [1, 2]],
    [1, 4, [1, 2, 3, 4]],
    [4, 4, [1, 2, 3, 4]],
    [3, 5, [1, 2, 3, 4, 5]],
  ])('con menos de 5 páginas o justo 5, la actual %i de %i muestra todas', (actual, total, esperadas) => {
    expect(ventanaDePaginas(actual, total)).toEqual(esperadas);
  });

  test.each([
    [1, 10, [1, 2, 3, 4, 5]],
    [2, 10, [1, 2, 3, 4, 5]],
    [3, 10, [1, 2, 3, 4, 5]],
    [4, 10, [2, 3, 4, 5, 6]],
    [5, 10, [3, 4, 5, 6, 7]],
    [8, 10, [6, 7, 8, 9, 10]],
    [9, 10, [6, 7, 8, 9, 10]],
    [10, 10, [6, 7, 8, 9, 10]],
  ])('la actual %i de %i muestra siempre 5 páginas, completando hacia el otro lado', (actual, total, esperadas) => {
    expect(ventanaDePaginas(actual, total)).toEqual(esperadas);
  });

  test('en el centro muestra la actual y dos a cada lado', () => {
    expect(ventanaDePaginas(50, 100)).toEqual([48, 49, 50, 51, 52]);
  });

  test('siempre incluye la página actual', () => {
    for (let total = 1; total <= 12; total += 1) {
      for (let actual = 1; actual <= total; actual += 1) {
        const ventana = ventanaDePaginas(actual, total);
        expect(ventana).toContain(actual);
        expect(ventana).toHaveLength(Math.min(5, total));
        expect(ventana[0]).toBeGreaterThanOrEqual(1);
        expect(ventana.at(-1)).toBeLessThanOrEqual(total);
      }
    }
  });

  test('admite otra cantidad de botones', () => {
    expect(ventanaDePaginas(5, 20, 3)).toEqual([4, 5, 6]);
  });
});

describe('totalDePaginas', () => {
  test.each([
    [0, 1],
    [1, 1],
    [20, 1],
    [21, 2],
    [40, 2],
    [41, 3],
  ])('%i elementos de a 20 son %i páginas', (cantidad, esperadas) => {
    expect(totalDePaginas(cantidad)).toBe(esperadas);
  });

  test('admite otro tamaño de página', () => {
    expect(totalDePaginas(45, 10)).toBe(5);
  });
});
