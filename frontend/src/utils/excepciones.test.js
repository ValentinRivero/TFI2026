import { describe, expect, test } from 'vitest';
import {
  aParametrosExcepciones,
  cuerpoExcepcion,
  FILTROS_EXCEPCIONES_INICIALES,
  validarExcepcion,
  VALORES_EXCEPCION_INICIALES,
} from './excepciones.js';

const HOY = '2026-11-12';
const valido = {
  ...VALORES_EXCEPCION_INICIALES,
  fecha_inicio: '2026-11-20',
  fecha_fin: '2026-11-22',
  tipo_motivo: '3',
};

describe('aParametrosExcepciones', () => {
  test('por defecto pide las vigentes del complejo en la página indicada', () => {
    expect(aParametrosExcepciones(5, FILTROS_EXCEPCIONES_INICIALES, 2)).toEqual({
      complejo: 5, page: 2, vigencia: 'vigentes',
    });
  });

  test('suma los filtros activos con el nombre que usa la API', () => {
    const filtros = { vigencia: '', cancha: '8', motivo: '1', fecha: '2026-12-01' };

    expect(aParametrosExcepciones(5, filtros, 1)).toEqual({
      complejo: 5, page: 1, cancha: '8', tipo_motivo: '1', fecha: '2026-12-01',
    });
  });

  test('una fecha que no existe no viaja', () => {
    expect(aParametrosExcepciones(5, { ...FILTROS_EXCEPCIONES_INICIALES, fecha: '2026-02-31' }, 1)).not.toHaveProperty('fecha');
  });
});

describe('validarExcepcion', () => {
  test('un día completo válido no tiene errores', () => {
    expect(validarExcepcion(valido, HOY)).toEqual({});
  });

  test('exige fechas de calendario, no anteriores a hoy, y un fin igual o posterior', () => {
    expect(validarExcepcion({ ...valido, fecha_inicio: '', fecha_fin: '' }, HOY)).toHaveProperty('fecha_inicio');
    expect(validarExcepcion({ ...valido, fecha_inicio: '2026-11-11' }, HOY)).toHaveProperty('fecha_inicio');
    expect(validarExcepcion({ ...valido, fecha_fin: '2026-11-19' }, HOY)).toHaveProperty('fecha_fin');
    expect(validarExcepcion({ ...valido, fecha_inicio: '2026-11-12', fecha_fin: '2026-11-12' }, HOY)).toEqual({});
  });

  test('exige el motivo y, si afecta a una cancha, cuál', () => {
    const errores = validarExcepcion({ ...valido, tipo_motivo: '', alcance: 'cancha' }, HOY);

    expect(Object.keys(errores).sort()).toEqual(['cancha', 'tipo_motivo']);
  });

  test('una franja exige ambas horas y un fin posterior al inicio', () => {
    const franja = { ...valido, es_dia_completo: '0' };

    expect(Object.keys(validarExcepcion(franja, HOY)).sort()).toEqual(['hora_fin', 'hora_inicio']);
    expect(validarExcepcion({ ...franja, hora_inicio: '18:00', hora_fin: '17:00' }, HOY)).toHaveProperty('hora_fin');
    expect(validarExcepcion({ ...franja, hora_inicio: '18:00', hora_fin: '20:00' }, HOY)).toEqual({});
  });
});

describe('cuerpoExcepcion', () => {
  test('un día completo de todo el complejo va sin cancha ni horas', () => {
    expect(cuerpoExcepcion(5, { ...valido, descripcion: ' Feriado local ' })).toEqual({
      complejo: 5,
      cancha: null,
      fecha_inicio: '2026-11-20',
      fecha_fin: '2026-11-22',
      es_dia_completo: 1,
      hora_inicio: null,
      hora_fin: null,
      tipo_motivo: 3,
      descripcion: 'Feriado local',
    });
  });

  test('una franja sobre una cancha lleva el id numérico y las horas', () => {
    const cuerpo = cuerpoExcepcion(5, {
      ...valido, alcance: 'cancha', cancha: '8', es_dia_completo: '0', hora_inicio: '18:00', hora_fin: '20:00',
    });

    expect(cuerpo).toMatchObject({ cancha: 8, es_dia_completo: 0, hora_inicio: '18:00', hora_fin: '20:00' });
  });
});
