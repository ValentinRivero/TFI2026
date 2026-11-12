import { describe, expect, test } from 'vitest';
import { CANCELACION, estadoDeCancelacion, nacerSinCancelacion } from './reservas.js';

// Todo en hora local: el turno es el 24/11 de 20:00 a 21:00 y el margen vence a las 16:00 de ese día.
const momento = (dia, hora) => new Date(2026, 10, dia, hora, 0);

const reserva = (cambios = {}) => ({
  estado: 2,
  fecha_turno: '2026-11-24',
  hora_inicio: '20:00:00',
  hora_fin: '21:00:00',
  cancelable_hasta: momento(24, 16).toISOString(),
  ...cambios,
});

describe('estadoDeCancelacion', () => {
  test('permite cancelar mientras falte más que el margen', () => {
    expect(estadoDeCancelacion(reserva(), momento(24, 12))).toBe(CANCELACION.PERMITIDA);
  });

  test('pasado el margen y antes de que termine el turno, queda fuera de margen', () => {
    expect(estadoDeCancelacion(reserva(), momento(24, 18))).toBe(CANCELACION.FUERA_DE_MARGEN);
  });

  test('con el turno en curso sigue fuera de margen', () => {
    expect(estadoDeCancelacion(reserva(), momento(24, 20))).toBe(CANCELACION.FUERA_DE_MARGEN);
  });

  test('una reserva cuyo turno ya terminó no ofrece cancelar ni informa margen', () => {
    expect(estadoDeCancelacion(reserva({ estado: 3 }), momento(24, 22))).toBe(CANCELACION.NO_APLICA);
  });

  test.each([0, 4, 5, 6, 7])('el estado %i no es cancelable', (estado) => {
    expect(estadoDeCancelacion(reserva({ estado }), momento(20, 12))).toBe(CANCELACION.NO_APLICA);
  });

  test.each([1, 2, 3])('el estado %i es cancelable dentro del margen', (estado) => {
    expect(estadoDeCancelacion(reserva({ estado }), momento(20, 12))).toBe(CANCELACION.PERMITIDA);
  });

  test('un límite ilegible se trata como fuera de margen y deja decidir al servidor', () => {
    expect(estadoDeCancelacion(reserva({ cancelable_hasta: null }), momento(20, 12))).toBe(CANCELACION.FUERA_DE_MARGEN);
  });
});

describe('nacerSinCancelacion', () => {
  test('avisa cuando faltan menos horas que el margen (turno de las 17:00, margen de 4 horas, son las 15:00)', () => {
    expect(nacerSinCancelacion('2026-11-24', '17:00:00', 4, momento(24, 15))).toBe(true);
  });

  test('no avisa cuando falta más que el margen', () => {
    expect(nacerSinCancelacion('2026-11-24', '20:00:00', 4, momento(24, 15))).toBe(false);
  });

  test('en el límite exacto ya no se puede cancelar, igual que en el servidor', () => {
    expect(nacerSinCancelacion('2026-11-24', '19:00:00', 4, momento(24, 15))).toBe(true);
    expect(nacerSinCancelacion('2026-11-24', '19:01', 4, momento(24, 15))).toBe(false);
  });

  test('un margen que cruza la medianoche se calcula sobre el instante, no sobre el día', () => {
    expect(nacerSinCancelacion('2026-11-25', '01:00:00', 4, momento(24, 22))).toBe(true);
    expect(nacerSinCancelacion('2026-11-25', '03:00:00', 4, momento(24, 22))).toBe(false);
  });

  test('un turno de otro día con margen corto no avisa', () => {
    expect(nacerSinCancelacion('2026-11-26', '17:00:00', 4, momento(24, 15))).toBe(false);
  });

  test('sin margen configurado o con datos inválidos no avisa', () => {
    expect(nacerSinCancelacion('2026-11-24', '17:00:00', 0, momento(24, 16))).toBe(false);
    expect(nacerSinCancelacion('2026-11-24', '17:00:00', undefined, momento(24, 16))).toBe(false);
    expect(nacerSinCancelacion('mañana', '17:00:00', 4, momento(24, 15))).toBe(false);
    expect(nacerSinCancelacion('2026-11-24', 'tarde', 4, momento(24, 15))).toBe(false);
  });
});
