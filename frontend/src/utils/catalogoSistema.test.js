import { describe, expect, test } from 'vitest';
import { t } from '../i18n/index.js';
import { CATALOGOS_SISTEMA, normalizarNombre, textoDeUsos, validarNombreCatalogo } from './catalogoSistema.js';

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
