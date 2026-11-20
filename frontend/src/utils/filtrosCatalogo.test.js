import { describe, expect, test } from 'vitest';
import { t } from '../i18n/index.js';
import {
  FILTROS_VACIOS, alternarElegido, aParametros, conVista, contarFiltros, hayFiltros, leerFiltros, leerVista, mostrarGuiaDeUso,
} from './filtrosCatalogo.js';

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

describe('leerVista y conVista', () => {
  test('la lista es la vista de origen y solo ?vista=mapa abre el mapa', () => {
    expect(leerVista(new URLSearchParams(''))).toBe('lista');
    expect(leerVista(new URLSearchParams('vista=otra'))).toBe('lista');
    expect(leerVista(new URLSearchParams('vista=mapa'))).toBe('mapa');
  });

  test('el mapa viaja en la URL junto a los filtros y la lista no escribe nada', () => {
    const filtros = { ...FILTROS_VACIOS, deporte: '2' };

    expect(conVista(aParametros(filtros), 'mapa').toString()).toBe('deporte=2&vista=mapa');
    expect(conVista(aParametros(filtros), 'lista').toString()).toBe('deporte=2');
  });

  test('la vista no altera los filtros leídos', () => {
    const parametros = conVista(aParametros({ ...FILTROS_VACIOS, search: 'goya' }), 'mapa');

    expect(leerFiltros(parametros)).toEqual({ ...FILTROS_VACIOS, search: 'goya' });
  });
});

describe('mostrarGuiaDeUso', () => {
  test('sin filtros y en la lista se muestra', () => {
    expect(mostrarGuiaDeUso(FILTROS_VACIOS, 'lista')).toBe(true);
  });

  test('en el mapa se oculta aunque no haya filtros', () => {
    expect(mostrarGuiaDeUso(FILTROS_VACIOS, 'mapa')).toBe(false);
  });

  test.each([
    ['un deporte', { deporte: '2' }],
    ['una cobertura', { cobertura: '1' }],
    ['un servicio', { servicios: ['4'] }],
    ['una búsqueda', { search: 'yacaré' }],
    ['un orden', { ordering: '-precio_desde' }],
  ])('con %s se oculta', (_nombre, cambios) => {
    expect(mostrarGuiaDeUso({ ...FILTROS_VACIOS, ...cambios }, 'lista')).toBe(false);
  });

  test('una búsqueda de solo espacios no cuenta como filtro', () => {
    expect(mostrarGuiaDeUso({ ...FILTROS_VACIOS, search: '   ' }, 'lista')).toBe(true);
  });
});

describe('alternarElegido', () => {
  test('agrega un id que no estaba, como texto y al final', () => {
    expect(alternarElegido(['2'], 5)).toEqual(['2', '5']);
  });

  test('quita un id que ya estaba, sea número o texto', () => {
    expect(alternarElegido(['2', '5'], 2)).toEqual(['5']);
    expect(alternarElegido(['2', '5'], '5')).toEqual(['2']);
  });

  test('no modifica la lista original', () => {
    const original = Object.freeze(['1']);

    expect(alternarElegido(original, 3)).toEqual(['1', '3']);
    expect(original).toEqual(['1']);
  });

  test('la selección múltiple viaja como servicio repetido y vuelve igual de la URL', () => {
    const elegidos = alternarElegido(alternarElegido([], 4), 7);
    const parametros = aParametros({ ...FILTROS_VACIOS, servicios: elegidos });

    expect(parametros.toString()).toBe('servicio=4&servicio=7');
    expect(leerFiltros(parametros).servicios).toEqual(['4', '7']);
  });

  test('desmarcar el último deja la selección vacía y sin parámetros', () => {
    expect(aParametros({ ...FILTROS_VACIOS, servicios: alternarElegido(['4'], 4) }).toString()).toBe('');
  });
});

describe('textos del filtro de servicios', () => {
  test('etiquetas del desplegable', () => {
    expect(t('filtros.servicios')).toBe('Servicios');
    expect(t('filtros.cualquierServicio')).toBe('Cualquier servicio');
    expect(t('filtros.serviciosConCantidad', { cantidad: 2 })).toBe('Servicios (2)');
    expect(t('filtros.limpiarServicios')).toBe('Limpiar selección');
    expect(t('filtros.seleccionados', { cantidad: 3 })).toBe('Seleccionados: 3');
  });
});
