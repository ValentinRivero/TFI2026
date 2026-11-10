import { diasDelRango, inicioDelDia, ZONA_HORARIA } from '../utils/fechas.js';

describe('fechas en hora de Argentina', () => {
  test('el día empieza a las 00:00 de Argentina, 03:00 UTC', () => {
    expect(inicioDelDia('2026-11-10').toISOString()).toBe('2026-11-10T03:00:00.000Z');
    expect(ZONA_HORARIA).toBe('-03:00');
  });

  test('lista cada día del rango, ambos extremos incluidos', () => {
    expect(diasDelRango('2026-11-29', '2026-12-02')).toEqual(['2026-11-29', '2026-11-30', '2026-12-01', '2026-12-02']);
  });

  test('un rango de un solo día tiene ese día', () => {
    expect(diasDelRango('2026-11-10', '2026-11-10')).toEqual(['2026-11-10']);
  });

  test('cruza el 29 de febrero de un año bisiesto', () => {
    expect(diasDelRango('2028-02-28', '2028-03-01')).toEqual(['2028-02-28', '2028-02-29', '2028-03-01']);
  });
});
