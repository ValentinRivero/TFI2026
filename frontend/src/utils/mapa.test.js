import { describe, expect, test } from 'vitest';
import {
  armarMarcadores, esClicSimple, htmlAtribucion, htmlAtribuciones, limitesDe, rutaDeComplejo,
} from './mapa.js';

const punto = (cambios = {}) => ({
  id: 1, nombre: 'Complejo El Yacaré', latitud: '-29.140000', longitud: '-59.260000', precio_desde: '38000.00', ...cambios,
});

describe('armarMarcadores', () => {
  test('convierte las coordenadas de texto a número', () => {
    expect(armarMarcadores([punto()])).toEqual([
      { id: 1, nombre: 'Complejo El Yacaré', posicion: [-29.14, -59.26], precioDesde: '38000.00' },
    ]);
  });

  test('un complejo sin precio queda con precioDesde en null', () => {
    expect(armarMarcadores([punto({ precio_desde: null })])[0].precioDesde).toBeNull();
    expect(armarMarcadores([punto({ precio_desde: undefined })])[0].precioDesde).toBeNull();
  });

  test('descarta los que no tienen coordenadas válidas', () => {
    const lista = [
      punto({ id: 2, latitud: null }),
      punto({ id: 3, longitud: '' }),
      punto({ id: 4, latitud: 'abc' }),
      punto({ id: 5, latitud: '95' }),
      punto({ id: 6, longitud: '-181' }),
      punto({ id: 7 }),
    ];

    expect(armarMarcadores(lista).map(({ id }) => id)).toEqual([7]);
  });

  test('descarta los registros sin id y tolera entradas inesperadas', () => {
    expect(armarMarcadores([punto({ id: undefined }), null, undefined])).toEqual([]);
    expect(armarMarcadores(null)).toEqual([]);
    expect(armarMarcadores(undefined)).toEqual([]);
  });

  test('acepta coordenadas numéricas dentro de Goya', () => {
    expect(armarMarcadores([punto({ latitud: -29.15, longitud: -59.25 })])[0].posicion).toEqual([-29.15, -59.25]);
  });

  test('descarta los complejos fuera del área de Goya a la que se limita el mapa', () => {
    const lista = [
      punto({ id: 2, latitud: '0', longitud: '0' }),
      punto({ id: 3, latitud: '-34.60', longitud: '-58.38' }),
      punto({ id: 4, latitud: '-29.0', longitud: '-59.26' }),
      punto({ id: 5, latitud: '-29.14', longitud: '-59.40' }),
      punto({ id: 6, latitud: '-29.22', longitud: '-59.34' }),
    ];

    expect(armarMarcadores(lista).map(({ id }) => id)).toEqual([6]);
  });
});

describe('limitesDe', () => {
  test('sin marcadores no hay límites', () => {
    expect(limitesDe([])).toBeNull();
  });

  test('con uno solo, las dos esquinas coinciden', () => {
    expect(limitesDe(armarMarcadores([punto()]))).toEqual([[-29.14, -59.26], [-29.14, -59.26]]);
  });

  test('devuelve las esquinas sur-oeste y norte-este', () => {
    const marcadores = armarMarcadores([
      punto({ id: 1, latitud: '-29.10', longitud: '-59.30' }),
      punto({ id: 2, latitud: '-29.20', longitud: '-59.20' }),
      punto({ id: 3, latitud: '-29.15', longitud: '-59.25' }),
    ]);

    expect(limitesDe(marcadores)).toEqual([[-29.2, -59.3], [-29.1, -59.2]]);
  });
});

describe('htmlAtribucion y htmlAtribuciones', () => {
  const osm = { texto: '© OpenStreetMap contributors', url: 'https://www.openstreetmap.org/copyright', licencia: 'ODbL' };
  const esri = { texto: 'Tiles © Esri', url: 'https://www.esri.com/', licencia: 'Esri World Street Map' };

  test('enlaza al sitio, con la licencia en el title y sin exponer al opener', () => {
    const html = htmlAtribucion(osm);

    expect(html).toContain('href="https://www.openstreetmap.org/copyright"');
    expect(html).toContain('title="ODbL"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('>© OpenStreetMap contributors</a>');
  });

  test('escapa los caracteres que cerrarían un atributo', () => {
    const html = htmlAtribucion({ ...osm, licencia: '"><script>', texto: '<b>' });

    expect(html).not.toContain('<script>');
    expect(html).toContain('&quot;&gt;&lt;script&gt;');
    expect(html).toContain('&lt;b&gt;');
  });

  test('junta las atribuciones de una capa, una por proveedor', () => {
    const html = htmlAtribuciones([osm, esri]);

    expect(html.match(/<a /g)).toHaveLength(2);
    expect(html).toContain('title="Esri World Street Map"');
    expect(htmlAtribuciones([])).toBe('');
  });
});

describe('rutaDeComplejo y esClicSimple', () => {
  test('arma la ruta del detalle y codifica el id', () => {
    expect(rutaDeComplejo(12)).toBe('/complejos/12');
    expect(rutaDeComplejo('a/b')).toBe('/complejos/a%2Fb');
  });

  test('solo el botón principal sin modificadores es un clic simple', () => {
    expect(esClicSimple({ button: 0 })).toBe(true);
    expect(esClicSimple({ button: 1 })).toBe(false);
    expect(esClicSimple({ button: 0, ctrlKey: true })).toBe(false);
    expect(esClicSimple({ button: 0, metaKey: true })).toBe(false);
    expect(esClicSimple({ button: 0, shiftKey: true })).toBe(false);
  });
});
