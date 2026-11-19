import { describe, expect, test } from 'vitest';
import { pronosticoDeFecha } from './clima.js';

const CLIMA = {
  actual: { temperatura: 30 },
  pronostico: [
    { fecha: '2026-11-12', temperatura_max: 34 },
    { fecha: '2026-11-13', temperatura_max: 33 },
    { fecha: '2026-11-14', temperatura_max: 30 },
  ],
};

describe('pronosticoDeFecha', () => {
  test('devuelve el día pedido dentro del pronóstico', () => {
    expect(pronosticoDeFecha(CLIMA, '2026-11-13')).toEqual({ fecha: '2026-11-13', temperatura_max: 33 });
  });

  test('una fecha fuera de los días informados da null', () => {
    expect(pronosticoDeFecha(CLIMA, '2026-11-15')).toBeNull();
    expect(pronosticoDeFecha(CLIMA, '2026-11-11')).toBeNull();
  });

  test('sin clima o sin pronóstico da null', () => {
    expect(pronosticoDeFecha(null, '2026-11-13')).toBeNull();
    expect(pronosticoDeFecha({ actual: {} }, '2026-11-13')).toBeNull();
  });
});
