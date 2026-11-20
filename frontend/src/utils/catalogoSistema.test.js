import { describe, expect, test } from 'vitest';
import { t } from '../i18n/index.js';
import {
  CATALOGOS_SISTEMA,
  filtrarCatalogo,
  FILTROS_CATALOGO_INICIALES,
  hayFiltroActivo,
  normalizarNombre,
  normalizarParaBuscar,
  textoDeUsos,
  validarNombreCatalogo,
} from './catalogoSistema.js';

describe('normalizarNombre', () => {
  test('quita los espacios de los extremos y simplifica los internos', () => {
    expect(normalizarNombre('  Fútbol   5 ')).toBe('Fútbol 5');
  });

  test('un valor ausente es un texto vacío', () => {
    expect(normalizarNombre(undefined)).toBe('');
    expect(normalizarNombre(null)).toBe('');
  });
});

describe('validarNombreCatalogo', () => {
  test('el nombre es obligatorio, también si solo tiene espacios', () => {
    expect(validarNombreCatalogo('', 'deportes')).toBe(t('catalogoSistema.errorNombreVacio'));
    expect(validarNombreCatalogo('    ', 'servicios')).toBe(t('catalogoSistema.errorNombreVacio'));
  });

  test('exige al menos dos caracteres', () => {
    expect(validarNombreCatalogo('A', 'deportes')).toBe(t('catalogoSistema.errorNombreCorto', { minimo: 2 }));
    expect(validarNombreCatalogo(' A ', 'servicios')).toBe(t('catalogoSistema.errorNombreCorto', { minimo: 2 }));
    expect(validarNombreCatalogo('Ab', 'deportes')).toBeUndefined();
  });

  test('un deporte admite hasta 60 caracteres', () => {
    expect(validarNombreCatalogo('a'.repeat(60), 'deportes')).toBeUndefined();
    expect(validarNombreCatalogo('a'.repeat(61), 'deportes')).toBe(t('catalogoSistema.errorNombreLargo', { maximo: 60 }));
  });

  test('un servicio admite hasta 80 caracteres', () => {
    expect(validarNombreCatalogo('a'.repeat(80), 'servicios')).toBeUndefined();
    expect(validarNombreCatalogo('a'.repeat(81), 'servicios')).toBe(t('catalogoSistema.errorNombreLargo', { maximo: 80 }));
  });

  test('el largo se mide con los espacios ya simplificados, como los guarda el backend', () => {
    expect(validarNombreCatalogo(`${'a'.repeat(58)}      b`, 'deportes')).toBeUndefined();
  });
});

describe('textoDeUsos', () => {
  test('los deportes cuentan canchas y los servicios, complejos', () => {
    expect(textoDeUsos('deportes', 1)).toBe('1 cancha');
    expect(textoDeUsos('deportes', 3)).toBe('3 canchas');
    expect(textoDeUsos('servicios', 1)).toBe('1 complejo');
    expect(textoDeUsos('servicios', 0)).toBe('0 complejos');
  });
});

describe('CATALOGOS_SISTEMA', () => {
  test('cada catálogo apunta a su ruta administrativa', () => {
    expect(CATALOGOS_SISTEMA.deportes.ruta).toBe('/api/sistema/deportes/');
    expect(CATALOGOS_SISTEMA.servicios.ruta).toBe('/api/sistema/servicios/');
  });

  test.each(Object.keys(CATALOGOS_SISTEMA))('%s tiene todos los textos de su pantalla', (recurso) => {
    const { textos } = CATALOGOS_SISTEMA[recurso];
    const claves = [
      'titulo', 'descripcion', 'nuevo', 'tituloAlta', 'tituloEdicion', 'campoNombre', 'usosUno', 'usosVarios',
      'resumen', 'errorTitulo', 'vacioTitulo', 'vacioDescripcion', 'bajaTitulo', 'bajaTexto', 'bajaTextoEnUso',
    ];

    claves.forEach((clave) => {
      expect(t(`${textos}.${clave}`), `${textos}.${clave}`).not.toBe(`${textos}.${clave}`);
    });
  });
});

describe('pestañas de /sistema y acceso al panel', () => {
  test.each(['usuarios', 'roles', 'contratos', 'deportes', 'servicios', 'auditoria'])('existe el texto de la pestaña %s', (clave) => {
    expect(t(`sistema.${clave}`)).not.toBe(`sistema.${clave}`);
  });

  test('el botón de cada contrato tiene su texto', () => {
    expect(t('contratos.administrar')).toBe('Administrar complejo');
  });
});

describe('normalizarParaBuscar', () => {
  test('ignora mayúsculas, tildes y espacios de los extremos', () => {
    expect(normalizarParaBuscar('  PÁDEL Ñandú ')).toBe('padel nandu');
  });

  test('un valor ausente es un texto vacío', () => {
    expect(normalizarParaBuscar(undefined)).toBe('');
    expect(normalizarParaBuscar(null)).toBe('');
  });
});

describe('filtrarCatalogo', () => {
  const items = Object.freeze([
    Object.freeze({ id: 1, nombre: 'Fútbol 5', estado: 1 }),
    Object.freeze({ id: 2, nombre: 'Fútbol 7', estado: 0 }),
    Object.freeze({ id: 3, nombre: 'Pádel', estado: 1 }),
    Object.freeze({ id: 4, nombre: 'Básquet', estado: 0 }),
  ]);
  const ids = (resultado) => resultado.map((item) => item.id);

  test('sin filtros devuelve todo, en el mismo orden', () => {
    expect(ids(filtrarCatalogo(items, FILTROS_CATALOGO_INICIALES))).toEqual([1, 2, 3, 4]);
  });

  test('busca sin distinguir mayúsculas ni tildes', () => {
    expect(ids(filtrarCatalogo(items, { busqueda: 'padel', estado: '' }))).toEqual([3]);
    expect(ids(filtrarCatalogo(items, { busqueda: 'FUTBOL', estado: '' }))).toEqual([1, 2]);
    expect(ids(filtrarCatalogo(items, { busqueda: 'básq', estado: '' }))).toEqual([4]);
  });

  test('todas las palabras escritas deben aparecer, en cualquier orden', () => {
    expect(ids(filtrarCatalogo(items, { busqueda: '7 futbol', estado: '' }))).toEqual([2]);
    expect(ids(filtrarCatalogo(items, { busqueda: 'futbol tenis', estado: '' }))).toEqual([]);
  });

  test('filtra por estado: activos (1) o de baja (0)', () => {
    expect(ids(filtrarCatalogo(items, { busqueda: '', estado: '1' }))).toEqual([1, 3]);
    expect(ids(filtrarCatalogo(items, { busqueda: '', estado: '0' }))).toEqual([2, 4]);
  });

  test('combina búsqueda y estado', () => {
    expect(ids(filtrarCatalogo(items, { busqueda: 'futbol', estado: '0' }))).toEqual([2]);
  });

  test('una búsqueda de solo espacios no filtra', () => {
    expect(ids(filtrarCatalogo(items, { busqueda: '   ', estado: '' }))).toEqual([1, 2, 3, 4]);
  });

  test('sin coincidencias devuelve una lista vacía y no modifica la original', () => {
    expect(filtrarCatalogo(items, { busqueda: 'natación', estado: '' })).toEqual([]);
    expect(items).toHaveLength(4);
  });

  test('puede buscar en otros textos del registro', () => {
    const roles = [{ id: 1, nombre: 'Cajero', descripcion: 'Cobra en el mostrador', estado: 1 }];
    const filtros = { busqueda: 'mostrador', estado: '' };

    expect(filtrarCatalogo(roles, filtros, (rol) => [rol.nombre, rol.descripcion])).toHaveLength(1);
    expect(filtrarCatalogo(roles, filtros)).toHaveLength(0);
  });
});

describe('hayFiltroActivo', () => {
  test('hay filtro con texto o con estado, pero no con espacios solos', () => {
    expect(hayFiltroActivo(FILTROS_CATALOGO_INICIALES)).toBe(false);
    expect(hayFiltroActivo({ busqueda: '   ', estado: '' })).toBe(false);
    expect(hayFiltroActivo({ busqueda: 'a', estado: '' })).toBe(true);
    expect(hayFiltroActivo({ busqueda: '', estado: '0' })).toBe(true);
  });
});

describe('redirección desde los usos', () => {
  test('los deportes llevan a las canchas del complejo y los servicios, a su configuración', () => {
    expect(CATALOGOS_SISTEMA.deportes.rutaPanel).toBe('/panel/canchas');
    expect(CATALOGOS_SISTEMA.servicios.rutaPanel).toBe('/panel');
  });
});

describe('textos de la búsqueda y del detalle de usos', () => {
  test.each([
    'catalogoSistema.filtros.etiqueta', 'catalogoSistema.filtros.estado', 'catalogoSistema.filtros.todos',
    'catalogoSistema.filtros.activos', 'catalogoSistema.filtros.baja', 'catalogoSistema.filtros.sinResultadosTitulo',
    'catalogoSistema.filtros.sinResultados', 'catalogoSistema.deportes.buscar', 'catalogoSistema.servicios.buscar',
    'roles.buscar', 'usos.titulo', 'usos.verDetalle', 'usos.errorTitulo', 'usos.errorMas', 'usos.vacio',
    'usos.deportes.titulo', 'usos.deportes.resumen', 'usos.deportes.canchas', 'usos.deportes.ir', 'usos.deportes.ayuda',
    'usos.servicios.titulo', 'usos.servicios.resumen', 'usos.servicios.ir', 'usos.servicios.ayuda',
    'usos.roles.titulo', 'usos.roles.resumen', 'usos.roles.ir', 'usos.roles.ayuda',
  ])('existe %s', (clave) => {
    expect(t(clave)).not.toBe(clave);
  });

  test('el nombre accesible del indicador de usos nombra el ítem y la cantidad', () => {
    expect(t('usos.verDetalle', { nombre: 'Pádel', cantidad: '3 canchas' })).toBe('Ver dónde está en uso «Pádel»: 3 canchas');
  });
});
