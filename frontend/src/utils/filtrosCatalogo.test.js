import { describe, expect, test } from 'vitest';
import { FILTROS_VACIOS, aParametros, contarFiltros, hayFiltros, leerFiltros } from './filtrosCatalogo.js';

const desde = (consulta) => leerFiltros(new URLSearchParams(consulta));

describe('leerFiltros', () => {
  test('sin parámetros devuelve los filtros vacíos', () => {
    expect(desde('')).toEqual(FILTROS_VACIOS);
  });

  test('lee cada filtro y los servicios repetidos', () => {
    expect(desde('deporte=2&cobertura=3&servicio=4&servicio=7&search=%20yacar%C3%A9%20&ordering=-precio_desde')).toEqual({
      deporte: '2',
      cobertura: '3',
      servicios: ['4', '7'],
      search: 'yacaré',
      ordering: '-precio_desde',
    });
  });

  test('descarta valores que el backend rechazaría', () => {
    expect(desde('deporte=abc&cobertura=9&servicio=x&servicio=-1&ordering=precio_base')).toEqual(FILTROS_VACIOS);
  });

  test('descarta ids con ceros a la izquierda o desmesurados', () => {
    expect(desde('deporte=007&servicio=12345678901')).toEqual(FILTROS_VACIOS);
  });

  test('quita los servicios repetidos', () => {
    expect(desde('servicio=3&servicio=3&servicio=5').servicios).toEqual(['3', '5']);
  });

  test('recorta la búsqueda al largo máximo', () => {
    expect(desde(`search=${'a'.repeat(300)}`).search).toHaveLength(100);
  });
});

describe('aParametros', () => {
  test('omite lo vacío', () => {
    expect(aParametros(FILTROS_VACIOS).toString()).toBe('');
  });

  test('repite servicio una vez por cada elegido', () => {
    const parametros = aParametros({ ...FILTROS_VACIOS, deporte: '1', servicios: ['2', '5'], search: ' cancha ' });

    expect(parametros.getAll('servicio')).toEqual(['2', '5']);
    expect(parametros.get('deporte')).toBe('1');
    expect(parametros.get('search')).toBe('cancha');
  });

  test('ida y vuelta con la URL', () => {
    const filtros = { deporte: '3', cobertura: '2', servicios: ['1', '9'], search: 'goya', ordering: 'nombre' };

    expect(leerFiltros(aParametros(filtros))).toEqual(filtros);
  });
});

describe('contarFiltros y hayFiltros', () => {
  test('el orden no cuenta como filtro pero sí se puede limpiar', () => {
    const solo = { ...FILTROS_VACIOS, ordering: 'nombre' };

    expect(contarFiltros(solo)).toBe(0);
    expect(hayFiltros(solo)).toBe(true);
    expect(hayFiltros(FILTROS_VACIOS)).toBe(false);
  });

  test('cuenta deporte, cobertura, búsqueda y cada servicio', () => {
    expect(contarFiltros({ deporte: '1', cobertura: '2', servicios: ['1', '2'], search: 'x', ordering: '' })).toBe(5);
  });

  test('una búsqueda de solo espacios no cuenta', () => {
    expect(contarFiltros({ ...FILTROS_VACIOS, search: '   ' })).toBe(0);
  });
});
