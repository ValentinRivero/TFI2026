import { readFileSync } from 'node:fs';
import { describe, expect, test, vi } from 'vitest';
import { PARAMETROS } from '../config/parametros.js';
import {
  alternarTema,
  aplicarTema,
  colorBarraDe,
  esTemaValido,
  guardarTema,
  leerTemaGuardado,
  resolverTema,
  temaDelSistema,
} from './tema.js';

const CLAVE = PARAMETROS.tema.claveAlmacenamiento;

const almacenConValor = (valor) => () => ({ getItem: (clave) => (clave === CLAVE ? valor : null) });
const almacenQueFalla = () => {
  throw new Error('almacenamiento bloqueado');
};
const medios = (oscuro) => vi.fn(() => ({ matches: oscuro }));

describe('esTemaValido', () => {
  test('acepta solo light y dark', () => {
    expect(esTemaValido('light')).toBe(true);
    expect(esTemaValido('dark')).toBe(true);
    expect(esTemaValido('auto')).toBe(false);
    expect(esTemaValido('DARK')).toBe(false);
    expect(esTemaValido(null)).toBe(false);
    expect(esTemaValido(undefined)).toBe(false);
  });
});

describe('leerTemaGuardado', () => {
  test('devuelve un valor guardado válido', () => {
    expect(leerTemaGuardado(almacenConValor('dark'))).toBe('dark');
    expect(leerTemaGuardado(almacenConValor('light'))).toBe('light');
  });

  test('un valor corrupto o inválido se ignora', () => {
    expect(leerTemaGuardado(almacenConValor('azul'))).toBeNull();
    expect(leerTemaGuardado(almacenConValor('{"tema":"dark"}'))).toBeNull();
    expect(leerTemaGuardado(almacenConValor(''))).toBeNull();
  });

  test('sin valor guardado devuelve null', () => {
    expect(leerTemaGuardado(almacenConValor(null))).toBeNull();
  });

  test('si el almacenamiento falla (al obtenerlo o al leerlo) devuelve null sin lanzar', () => {
    expect(leerTemaGuardado(almacenQueFalla)).toBeNull();
    expect(leerTemaGuardado(() => ({ getItem: almacenQueFalla }))).toBeNull();
  });
});

describe('guardarTema', () => {
  test('guarda un tema válido bajo la clave del tema', () => {
    const setItem = vi.fn();
    expect(guardarTema('dark', () => ({ setItem }))).toBe(true);
    expect(setItem).toHaveBeenCalledWith(CLAVE, 'dark');
  });

  test('no guarda un valor inválido', () => {
    const setItem = vi.fn();
    expect(guardarTema('azul', () => ({ setItem }))).toBe(false);
    expect(setItem).not.toHaveBeenCalled();
  });

  test('si el almacenamiento falla devuelve false sin lanzar', () => {
    expect(guardarTema('dark', almacenQueFalla)).toBe(false);
    expect(guardarTema('dark', () => ({ setItem: almacenQueFalla }))).toBe(false);
  });
});

describe('temaDelSistema', () => {
  test('con preferencia oscura devuelve dark y consulta prefers-color-scheme', () => {
    const consultar = medios(true);
    expect(temaDelSistema(consultar)).toBe('dark');
    expect(consultar).toHaveBeenCalledWith('(prefers-color-scheme: dark)');
  });

  test('con preferencia clara devuelve light', () => {
    expect(temaDelSistema(medios(false))).toBe('light');
  });

  test('sin soporte de matchMedia asume el modo claro', () => {
    expect(temaDelSistema(() => {
      throw new Error('sin matchMedia');
    })).toBe('light');
  });
});

describe('resolverTema', () => {
  test('la elección guardada manda sobre la preferencia del sistema', () => {
    expect(resolverTema({ guardado: 'light', sistema: 'dark' })).toBe('light');
    expect(resolverTema({ guardado: 'dark', sistema: 'light' })).toBe('dark');
  });

  test('sin elección guardada rige la preferencia del sistema, clara u oscura', () => {
    expect(resolverTema({ guardado: null, sistema: 'dark' })).toBe('dark');
    expect(resolverTema({ guardado: null, sistema: 'light' })).toBe('light');
  });

  test('una elección corrupta cae a la preferencia del sistema', () => {
    expect(resolverTema({ guardado: 'azul', sistema: 'dark' })).toBe('dark');
  });

  test('sin ningún dato válido queda en modo claro', () => {
    expect(resolverTema({})).toBe('light');
    expect(resolverTema()).toBe('light');
    expect(resolverTema({ guardado: null, sistema: 'x' })).toBe('light');
  });
});

describe('alternarTema', () => {
  test('pasa de claro a oscuro y de oscuro a claro', () => {
    expect(alternarTema('light')).toBe('dark');
    expect(alternarTema('dark')).toBe('light');
  });

  test('dos alternancias vuelven al tema original', () => {
    expect(alternarTema(alternarTema('dark'))).toBe('dark');
  });
});

describe('aplicarTema', () => {
  const documentoFalso = () => {
    const raiz = { setAttribute: vi.fn() };
    const meta = { setAttribute: vi.fn() };
    return {
      raiz,
      meta,
      documento: {
        documentElement: raiz,
        querySelector: vi.fn((selector) => (selector === 'meta[name="theme-color"]' ? meta : null)),
      },
    };
  };

  test('fija data-bs-theme y el color de la barra del navegador', () => {
    const { raiz, meta, documento } = documentoFalso();
    aplicarTema('dark', documento);
    expect(raiz.setAttribute).toHaveBeenCalledWith('data-bs-theme', 'dark');
    expect(meta.setAttribute).toHaveBeenCalledWith('content', colorBarraDe('dark'));
  });

  test('un tema inválido no toca el documento', () => {
    const { raiz, meta, documento } = documentoFalso();
    aplicarTema('azul', documento);
    expect(raiz.setAttribute).not.toHaveBeenCalled();
    expect(meta.setAttribute).not.toHaveBeenCalled();
  });

  test('sin etiqueta theme-color igual aplica el atributo', () => {
    const raiz = { setAttribute: vi.fn() };
    aplicarTema('light', { documentElement: raiz, querySelector: () => null });
    expect(raiz.setAttribute).toHaveBeenCalledWith('data-bs-theme', 'light');
  });
});

describe('espejo en index.html', () => {
  const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');

  test('el script de arranque usa la misma clave, consulta y colores que la aplicación', () => {
    expect(html).toContain(`getItem('${CLAVE}')`);
    expect(html).toContain(`matchMedia('${PARAMETROS.tema.consultaOscuro}')`);
    expect(html).toContain(`'${PARAMETROS.tema.colorBarra.dark}' : '${PARAMETROS.tema.colorBarra.light}'`);
    expect(html).toContain(`<meta name="theme-color" content="${PARAMETROS.tema.colorBarra.light}" />`);
  });
});
