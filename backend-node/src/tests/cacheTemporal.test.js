import { jest } from '@jest/globals';

import { crearCacheTemporal } from '../utils/cacheTemporal.js';

afterEach(() => {
  jest.restoreAllMocks();
});

const enElInstante = (ms) => jest.spyOn(Date, 'now').mockReturnValue(ms);

describe('crearCacheTemporal', () => {
  test('devuelve lo guardado hasta que vence', () => {
    const cache = crearCacheTemporal({ duracionMs: 1000, maximo: 10 });
    enElInstante(0);
    cache.guardar(1, 'a');

    enElInstante(999);
    expect(cache.obtener(1)).toBe('a');
    enElInstante(1000);
    expect(cache.obtener(1)).toBeUndefined();
  });

  test('al llenarse descarta la entrada más antigua', () => {
    const cache = crearCacheTemporal({ duracionMs: 1000, maximo: 2 });
    enElInstante(0);
    cache.guardar(1, 'a');
    cache.guardar(2, 'b');
    cache.guardar(3, 'c');

    expect(cache.obtener(1)).toBeUndefined();
    expect(cache.obtener(2)).toBe('b');
    expect(cache.obtener(3)).toBe('c');
  });

  test('guardar de nuevo una clave renueva su vencimiento sin ocupar otro lugar', () => {
    const cache = crearCacheTemporal({ duracionMs: 1000, maximo: 2 });
    enElInstante(0);
    cache.guardar(1, 'a');
    cache.guardar(2, 'b');
    enElInstante(500);
    cache.guardar(1, 'a2');
    cache.guardar(3, 'c');

    enElInstante(1200);
    expect(cache.obtener(1)).toBe('a2');
    expect(cache.obtener(2)).toBeUndefined();
  });

  test('borrar y vaciar quitan entradas', () => {
    const cache = crearCacheTemporal({ duracionMs: 1000, maximo: 5 });
    cache.guardar(1, 'a');
    cache.guardar(2, 'b');

    cache.borrar(1);
    expect(cache.obtener(1)).toBeUndefined();
    cache.vaciar();
    expect(cache.obtener(2)).toBeUndefined();
  });
});
