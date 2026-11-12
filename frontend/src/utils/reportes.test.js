import { describe, expect, test } from 'vitest';
import {
  anchoDeBarra,
  aParametrosReporte,
  filasDeConteo,
  filtrosReporteIniciales,
  maximoDe,
  tasaCancelacion,
  totalReservas,
  validarFiltrosReporte,
} from './reportes.js';

const CONTEOS = {
  pendientes: 3,
  confirmadas: 12,
  senadas: 5,
  canceladas_jugador: 4,
  canceladas_complejo: 1,
  canceladas_total: 5,
  ausentes: 2,
  completadas: 30,
};

describe('filtrosReporteIniciales', () => {
  test('abre desde el primer día del mes hasta hoy, por día de juego', () => {
    expect(filtrosReporteIniciales('2026-11-12')).toEqual({
      fecha_desde: '2026-11-01', fecha_hasta: '2026-11-12', criterio: 'fecha_turno', cancha: '', deporte: '',
    });
  });
});

describe('validarFiltrosReporte', () => {
  const base = filtrosReporteIniciales('2026-11-12');

  test('el rango inicial es válido', () => {
    expect(validarFiltrosReporte(base)).toEqual({});
  });

  test('exige fechas de calendario', () => {
    const errores = validarFiltrosReporte({ ...base, fecha_desde: '', fecha_hasta: '2026-02-31' });

    expect(Object.keys(errores).sort()).toEqual(['fecha_desde', 'fecha_hasta']);
  });

  test('la fecha final no puede ser anterior a la inicial', () => {
    expect(validarFiltrosReporte({ ...base, fecha_desde: '2026-11-12', fecha_hasta: '2026-11-11' })).toHaveProperty('fecha_hasta');
  });

  test('acepta un solo día y 366 días, y rechaza 367', () => {
    expect(validarFiltrosReporte({ ...base, fecha_desde: '2026-11-12', fecha_hasta: '2026-11-12' })).toEqual({});
    expect(validarFiltrosReporte({ ...base, fecha_desde: '2026-01-01', fecha_hasta: '2027-01-01' })).toEqual({});
    expect(validarFiltrosReporte({ ...base, fecha_desde: '2026-01-01', fecha_hasta: '2027-01-02' })).toHaveProperty('fecha_hasta');
  });
});

describe('aParametrosReporte', () => {
  test('usa los nombres de la API y omite los filtros vacíos', () => {
    expect(aParametrosReporte(5, filtrosReporteIniciales('2026-11-12'))).toEqual({
      complejo: 5, fecha_desde: '2026-11-01', fecha_hasta: '2026-11-12', criterio: 'fecha_turno',
    });
  });

  test('envía la cancha y el deporte como cancha_id y deporte_id', () => {
    const filtros = { ...filtrosReporteIniciales('2026-11-12'), cancha: '7', deporte: '2', criterio: 'fecha_creacion' };

    expect(aParametrosReporte(5, filtros)).toMatchObject({ cancha_id: '7', deporte_id: '2', criterio: 'fecha_creacion' });
  });
});

describe('totalReservas y tasaCancelacion', () => {
  test('el total suma todos los estados sin contar dos veces las canceladas', () => {
    expect(totalReservas(CONTEOS)).toBe(57);
  });

  test('la tasa es el porcentaje de canceladas sobre el total', () => {
    expect(tasaCancelacion(CONTEOS)).toBeCloseTo((5 / 57) * 100, 5);
  });

  test('un rango sin reservas da cero y no divide por cero', () => {
    const vacios = Object.fromEntries(Object.keys(CONTEOS).map((clave) => [clave, 0]));

    expect(totalReservas(vacios)).toBe(0);
    expect(tasaCancelacion(vacios)).toBe(0);
    expect(totalReservas(undefined)).toBe(0);
  });
});

describe('filasDeConteo', () => {
  test('devuelve un estado por fila, en el orden de los códigos de reserva', () => {
    const filas = filasDeConteo(CONTEOS);

    expect(filas.map((fila) => fila.estado)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(filas.map((fila) => fila.cantidad)).toEqual([3, 12, 5, 4, 1, 2, 30]);
  });
});

describe('anchoDeBarra y maximoDe', () => {
  test('el ancho es proporcional al máximo', () => {
    expect(anchoDeBarra(15, 30)).toBe(50);
    expect(anchoDeBarra(30, 30)).toBe(100);
    expect(anchoDeBarra(0, 30)).toBe(0);
  });

  test('sin máximo positivo o con valores inválidos la barra queda en cero y nunca pasa de 100', () => {
    expect(anchoDeBarra(5, 0)).toBe(0);
    expect(anchoDeBarra(null, 10)).toBe(0);
    expect(anchoDeBarra('abc', 10)).toBe(0);
    expect(anchoDeBarra(150, 100)).toBe(100);
    expect(anchoDeBarra(-5, 100)).toBe(0);
  });

  test('el máximo de una lista vacía es cero', () => {
    expect(maximoDe([], 'reservas')).toBe(0);
    expect(maximoDe(undefined, 'reservas')).toBe(0);
    expect(maximoDe([{ reservas: 3 }, { reservas: 18 }, { reservas: 7 }], 'reservas')).toBe(18);
  });
});
