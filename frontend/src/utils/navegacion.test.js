import { describe, expect, test } from 'vitest';
import { enlaceActivo } from './navegacion.js';

const RUTAS = ['/', '/mis-reservas', '/panel', '/panel/reportes', '/perfil'];

describe('enlaceActivo', () => {
  test('la portada solo está activa en la ruta exacta', () => {
    expect(enlaceActivo('/', RUTAS)).toBe('/');
    expect(enlaceActivo('/complejos/3', RUTAS)).toBeNull();
  });

  test('cada sección está activa en su ruta y en sus subrutas', () => {
    expect(enlaceActivo('/mis-reservas', RUTAS)).toBe('/mis-reservas');
    expect(enlaceActivo('/panel/agenda', RUTAS)).toBe('/panel');
  });

  test('con dos coincidencias gana la más específica, así nunca hay dos activos', () => {
    expect(enlaceActivo('/panel/reportes', RUTAS)).toBe('/panel/reportes');
    expect(enlaceActivo('/panel/reportes/2026', RUTAS)).toBe('/panel/reportes');
  });

  test('un prefijo que no es una subruta no coincide', () => {
    expect(enlaceActivo('/perfil-publico', RUTAS)).toBeNull();
    expect(enlaceActivo('/panelista', RUTAS)).toBeNull();
  });

  test('al volver a la portada deja de estar activa la sección anterior', () => {
    expect(enlaceActivo('/mis-reservas', RUTAS)).not.toBe(enlaceActivo('/', RUTAS));
  });
});
