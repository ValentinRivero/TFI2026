import { describe, expect, test } from 'vitest';
import {
  ajustarContador,
  aParametrosApi,
  aParametrosUrl,
  aplicarLeidas,
  clavesDeVacio,
  debeSondear,
  esUrgente,
  FILTROS_URGENTES,
  filtrosDeRegistro,
  filtrosUrgentesDe,
  leerFiltros,
  normalizarNotificacion,
  normalizarPagina,
  textoContador,
} from './notificaciones.js';

const FILTROS = { estado: 'no-leidas', prioridad: '', categoria: '', complejo: '' };

describe('leerFiltros', () => {
  test('sin query usa las no leídas y ningún otro filtro', () => {
    expect(leerFiltros(new URLSearchParams())).toEqual(FILTROS);
  });

  test('lee estado, prioridad y categoría válidos', () => {
    const filtros = leerFiltros(new URLSearchParams('estado=leidas&prioridad=2&categoria=3'));
    expect(filtros).toEqual({ estado: 'leidas', prioridad: '2', categoria: '3', complejo: '' });
  });

  test('lee el complejo si es un id', () => {
    expect(leerFiltros(new URLSearchParams('complejo=12')).complejo).toBe('12');
  });

  test.each(['0', '-3', '4.5', 'abc', '12abc', '%20'])('ignora un complejo que no es un id (%s)', (valor) => {
    expect(leerFiltros(new URLSearchParams({ complejo: valor })).complejo).toBe('');
  });

  test('ignora valores que los catálogos no conocen', () => {
    const filtros = leerFiltros(new URLSearchParams('estado=otro&prioridad=9&categoria=abc'));
    expect(filtros).toEqual(FILTROS);
  });
});

describe('aParametrosUrl', () => {
  test('los valores por defecto no ensucian la URL', () => {
    expect(aParametrosUrl(FILTROS)).toEqual({});
  });

  test('conserva solo lo que se aparta del valor por defecto', () => {
    expect(aParametrosUrl({ ...FILTROS, estado: 'todas', prioridad: '2' })).toEqual({ estado: 'todas', prioridad: '2' });
    expect(aParametrosUrl({ ...FILTROS, complejo: '7' })).toEqual({ complejo: '7' });
  });

  test('ida y vuelta con leerFiltros', () => {
    const filtros = { estado: 'leidas', prioridad: '1', categoria: '4', complejo: '9' };
    expect(leerFiltros(new URLSearchParams(aParametrosUrl(filtros)))).toEqual(filtros);
  });
});

describe('aParametrosApi', () => {
  test('no leídas viaja como estado 1 y la primera página no envía page', () => {
    expect(aParametrosApi(FILTROS)).toEqual({ estado: 1 });
  });

  test('todas no envía estado', () => {
    expect(aParametrosApi({ ...FILTROS, estado: 'todas' })).toEqual({});
  });

  test('suma categoría, prioridad, complejo y página', () => {
    const filtros = { estado: 'leidas', prioridad: '2', categoria: '3', complejo: '7' };
    expect(aParametrosApi(filtros, 3)).toEqual({
      complejo_id: '7', estado: 2, categoria: '3', prioridad: '2', page: 3,
    });
  });

  test('los avisos urgentes pendientes piden prioridad 2 y estado 1', () => {
    expect(aParametrosApi(FILTROS_URGENTES, 1)).toEqual({ estado: 1, prioridad: '2' });
  });

  test('el registro del complejo pide todas las entradas, sin estado ni complejo propio', () => {
    const filtros = { estado: 'no-leidas', prioridad: '2', categoria: '3', complejo: '5' };

    expect(filtrosDeRegistro(filtros)).toEqual({ estado: 'todas', prioridad: '2', categoria: '3', complejo: '' });
    expect(aParametrosApi(filtrosDeRegistro(filtros), 2)).toEqual({ categoria: '3', prioridad: '2', page: 2 });
  });

  test('los urgentes comparten solo el complejo elegido en la bandeja', () => {
    const filtros = { estado: 'todas', prioridad: '1', categoria: '3', complejo: '5' };

    expect(filtrosUrgentesDe(filtros)).toEqual({ ...FILTROS_URGENTES, complejo: '5' });
    expect(aParametrosApi(filtrosUrgentesDe(filtros))).toEqual({ complejo_id: '5', estado: 1, prioridad: '2' });
  });
});

describe('normalización de la respuesta de Node', () => {
  test('conserva id y acepta _id', () => {
    expect(normalizarNotificacion({ id: 'a1', mensaje: 'x' }).id).toBe('a1');
    expect(normalizarNotificacion({ _id: 'b2', mensaje: 'x' }).id).toBe('b2');
  });

  test('normaliza cada resultado de la página y completa lo que falta', () => {
    const pagina = normalizarPagina({ count: 2, next: '/x?page=2', results: [{ _id: 'a' }, { id: 'b' }] });
    expect(pagina.results.map(({ id }) => id)).toEqual(['a', 'b']);
    expect(pagina).toMatchObject({ count: 2, next: '/x?page=2', previous: null });
  });

  test('una respuesta vacía no rompe', () => {
    expect(normalizarPagina(undefined)).toEqual({ count: 0, next: null, previous: null, results: [] });
  });
});

describe('esUrgente', () => {
  test('solo la prioridad 2 es urgente', () => {
    expect(esUrgente({ prioridad: 2 })).toBe(true);
    expect(esUrgente({ prioridad: 1 })).toBe(false);
  });
});

describe('aplicarLeidas', () => {
  const lista = [
    { id: 'a', estado: 1 },
    { id: 'b', estado: 1 },
    { id: 'c', estado: 2 },
  ];

  test('sin marcas devuelve la misma lista', () => {
    expect(aplicarLeidas(lista, [], false)).toBe(lista);
  });

  test('en una bandeja de no leídas las oculta', () => {
    expect(aplicarLeidas(lista, ['a'], true).map(({ id }) => id)).toEqual(['b', 'c']);
  });

  test('en una bandeja con todas las pasa a leídas sin tocar las demás', () => {
    const resultado = aplicarLeidas(lista, ['b'], false);
    expect(resultado.map(({ estado }) => estado)).toEqual([1, 2, 2]);
    expect(lista[1].estado).toBe(1);
  });
});

describe('contador de la campana', () => {
  test('ajustarContador no baja de cero y respeta el desconocido', () => {
    expect(ajustarContador(3, -1)).toBe(2);
    expect(ajustarContador(0, -1)).toBe(0);
    expect(ajustarContador(null, -1)).toBeNull();
  });

  test('textoContador topa en 99+', () => {
    expect(textoContador(7)).toBe('7');
    expect(textoContador(99)).toBe('99');
    expect(textoContador(100)).toBe('99+');
    expect(textoContador(12, 10)).toBe('10+');
  });

  test('el sondeo se pausa solo con la pestaña oculta', () => {
    expect(debeSondear('visible')).toBe(true);
    expect(debeSondear('hidden')).toBe(false);
  });
});

describe('clavesDeVacio', () => {
  test('con categoría o prioridad sugiere ampliar la búsqueda', () => {
    expect(clavesDeVacio({ ...FILTROS, categoria: '1' }, 'x.generica').descripcion)
      .toBe('notificaciones.vacioFiltradasDescripcion');
  });

  test('con un complejo elegido también sugiere ampliar la búsqueda', () => {
    expect(clavesDeVacio({ ...FILTROS, complejo: '4' }, 'x.generica').descripcion)
      .toBe('notificaciones.vacioFiltradasDescripcion');
  });

  test('viendo no leídas informa que no hay pendientes', () => {
    expect(clavesDeVacio(FILTROS, 'x.generica').titulo).toBe('notificaciones.vacioNoLeidasTitulo');
  });

  test('en otro caso usa el texto propio de la bandeja', () => {
    expect(clavesDeVacio({ ...FILTROS, estado: 'todas' }, 'x.generica')).toEqual({
      titulo: 'notificaciones.vacioTitulo',
      descripcion: 'x.generica',
    });
  });
});
