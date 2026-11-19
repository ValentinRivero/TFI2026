import { paginar, TAMANO_DE_PAGINA } from '../utils/paginacion.js';

const RUTA = '/api/actividad';

describe('paginar', () => {
  test('una lista vacía tiene página 1, sin enlaces', () => {
    expect(paginar({ ruta: RUTA, filtros: {}, total: 0 })).toEqual({
      salto: 0, limite: TAMANO_DE_PAGINA, encabezado: { count: 0, next: null, previous: null },
    });
  });

  test('con exactamente 20 elementos hay una sola página', () => {
    expect(paginar({ ruta: RUTA, filtros: {}, total: 20 }).encabezado.next).toBeNull();
    expect(() => paginar({ ruta: RUTA, filtros: {}, pagina: 2, total: 20 })).toThrow('Página inválida.');
  });

  test('con 41 elementos la tercera página salta 40 y es la última', () => {
    const { salto, encabezado } = paginar({ ruta: RUTA, filtros: { complejo_id: 4 }, pagina: 3, total: 41 });

    expect(salto).toBe(40);
    expect(encabezado).toEqual({ count: 41, next: null, previous: '/api/actividad?complejo_id=4&page=2&limit=20' });
  });

  test('respeta un tamaño de página propio en el salto y en los enlaces', () => {
    const { salto, encabezado } = paginar({ ruta: RUTA, filtros: {}, pagina: 2, limite: 5, total: 12 });

    expect(salto).toBe(5);
    expect(encabezado.next).toBe('/api/actividad?page=3&limit=5');
  });

  test('una página posterior a la última es un 404', () => {
    expect(() => paginar({ ruta: RUTA, filtros: {}, pagina: 2, total: 0 })).toThrow(
      expect.objectContaining({ status: 404 }),
    );
  });
});
