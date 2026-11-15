import { describe, expect, test } from 'vitest';
import { describirCancha } from './cancha.js';

const base = { tipo_superficie: 1, cobertura: 2, iluminacion: 3, duracion_turno_min: 60 };

describe('describirCancha', () => {
  test('traduce los códigos con el catálogo', () => {
    expect(describirCancha(base)).toEqual({
      superficie: 'Césped sintético',
      cobertura: 'Techada',
      iluminacion: 'LED',
      duracion: '60 minutos',
    });
  });

  test('un código que el cliente no conoce usa el nombre que informa la API', () => {
    const cancha = { ...base, tipo_superficie: 99, tipo_superficie_nombre: 'Goma' };

    expect(describirCancha(cancha).superficie).toBe('Goma');
  });

  test('una duración fuera del catálogo se muestra en minutos', () => {
    expect(describirCancha({ ...base, duracion_turno_min: 75 }).duracion).toBe('75 minutos');
  });
});
