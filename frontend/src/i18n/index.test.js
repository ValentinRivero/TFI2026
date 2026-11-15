import { describe, expect, test, vi } from 'vitest';
import { t } from './index.js';

describe('t()', () => {
  test('devuelve el texto de una clave anidada', () => {
    expect(t('comun.cargando')).toBe('Cargando...');
  });

  test('reemplaza cada marcador %variable%', () => {
    expect(t('comun.resumenComplejos', { mostrados: 20, total: 53 })).toBe('Mostrando 20 de 53 complejos');
  });

  test('reemplaza varias veces el mismo marcador y acepta el cero', () => {
    expect(t('comun.resumenComplejos', { mostrados: 0, total: 0 })).toBe('Mostrando 0 de 0 complejos');
  });

  test('un marcador sin valor queda intacto', () => {
    expect(t('comun.resumenComplejos', { total: 7 })).toBe('Mostrando %mostrados% de 7 complejos');
    expect(t('comun.resumenComplejos')).toBe('Mostrando %mostrados% de %total% complejos');
  });

  test('un parámetro que el texto no usa se ignora', () => {
    expect(t('comun.cargando', { otro: 1 })).toBe('Cargando...');
  });

  test('una clave inexistente devuelve la clave y avisa en desarrollo', () => {
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {});

    expect(t('comun.no.existe')).toBe('comun.no.existe');
    expect(aviso).toHaveBeenCalledWith(expect.stringContaining('comun.no.existe'));
    aviso.mockRestore();
  });

  test('una clave que apunta a un grupo y no a un texto devuelve la clave', () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    expect(t('comun')).toBe('comun');
    vi.restoreAllMocks();
  });

  test('un idioma sin diccionario usa el español', () => {
    expect(t('comun.cargando', {}, 'xx')).toBe('Cargando...');
  });

  test('no interpreta HTML: el valor se devuelve como texto', () => {
    expect(t('guia.desde', { precio: '<b>1</b>' })).toBe('Desde <b>1</b> por turno');
  });

  test('un valor con un marcador adentro no se vuelve a reemplazar', () => {
    expect(t('comun.resumenComplejos', { mostrados: '%total%', total: 5 })).toBe('Mostrando %total% de 5 complejos');
  });
});
