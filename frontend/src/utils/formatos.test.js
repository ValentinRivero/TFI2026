import { describe, expect, test } from 'vitest';
import {
  aFechaIso,
  formatearFechaCorta,
  formatearFechaLarga,
  formatearHora,
  formatearPrecio,
  parsearFecha,
} from './formatos.js';

// Los espacios de Intl pueden ser no separables según la versión de ICU: se normalizan para comparar.
const normalizar = (texto) => texto.replace(/\s/g, ' ');

describe('parsearFecha', () => {
  test('arma la fecha por partes, en hora local', () => {
    const fecha = parsearFecha('2026-11-18');

    expect([fecha.getFullYear(), fecha.getMonth(), fecha.getDate()]).toEqual([2026, 10, 18]);
  });

  test('no corre el día aunque la zona horaria esté detrás de UTC', () => {
    const original = process.env.TZ;
    process.env.TZ = 'America/Argentina/Buenos_Aires';
    try {
      expect(parsearFecha('2026-01-01').getDate()).toBe(1);
      expect(parsearFecha('2026-01-01').getMonth()).toBe(0);
    } finally {
      if (original === undefined) delete process.env.TZ;
      else process.env.TZ = original;
    }
  });

  test.each(['2026-02-30', '2026-13-01', '2026-00-10', '2026-1-1', '18/11/2026', '', null, undefined])(
    'rechaza %s',
    (valor) => {
      expect(parsearFecha(valor)).toBeNull();
    },
  );

  test('acepta el 29 de febrero solo en año bisiesto', () => {
    expect(parsearFecha('2028-02-29')).not.toBeNull();
    expect(parsearFecha('2027-02-29')).toBeNull();
  });
});

describe('aFechaIso', () => {
  test('es la inversa de parsearFecha', () => {
    expect(aFechaIso(parsearFecha('2026-03-07'))).toBe('2026-03-07');
  });

  test('usa los componentes locales de la fecha', () => {
    expect(aFechaIso(new Date(2026, 11, 31, 23, 59))).toBe('2026-12-31');
  });
});

describe('formatearPrecio', () => {
  test('da formato de pesos argentinos', () => {
    expect(normalizar(formatearPrecio('38000.00'))).toBe('$ 38.000');
    expect(normalizar(formatearPrecio(1234567.5))).toBe('$ 1.234.567,50');
  });

  test('acepta texto decimal y números', () => {
    expect(formatearPrecio('42000.00')).toBe(formatearPrecio(42000));
  });

  test.each([null, undefined, '', 'abc'])('devuelve texto vacío para %s', (valor) => {
    expect(formatearPrecio(valor)).toBe('');
  });

  test('el cero es un precio válido', () => {
    expect(normalizar(formatearPrecio(0))).toBe('$ 0');
  });
});

describe('formatearHora', () => {
  test.each([
    ['14:00:00', '14:00'],
    ['08:30', '08:30'],
    ['9:05:00', '09:05'],
  ])('%s se muestra como %s', (entrada, esperada) => {
    expect(formatearHora(entrada)).toBe(esperada);
  });

  test.each([null, undefined, '', 'tarde'])('devuelve texto vacío para %s', (valor) => {
    expect(formatearHora(valor)).toBe('');
  });
});

describe('fechas legibles', () => {
  test('fecha larga con el día de la semana', () => {
    expect(formatearFechaLarga('2026-11-18')).toMatch(/miércoles,? 18 de noviembre/);
  });

  test('fecha corta día/mes/año', () => {
    expect(formatearFechaCorta('2026-11-08')).toBe('08/11/2026');
  });

  test('una fecha inválida devuelve texto vacío', () => {
    expect(formatearFechaLarga('2026-02-30')).toBe('');
    expect(formatearFechaCorta('mañana')).toBe('');
  });
});
