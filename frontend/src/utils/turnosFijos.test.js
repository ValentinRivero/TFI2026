import { describe, expect, test } from 'vitest';
import {
  aFilasEnEspera,
  aParametrosEnEspera,
  aParametrosTurnosFijos,
  bloquesDeHorarios,
  cuerpoTurnoFijo,
  FILTROS_TURNOS_FIJOS_INICIALES,
  proximasFechasDeTurnoFijo,
  validarTurnoFijo,
  VALORES_TURNO_FIJO_INICIALES,
} from './turnosFijos.js';

const HOY = '2026-11-12';

describe('aParametrosTurnosFijos', () => {
  test('sin filtros pide la primera página del complejo', () => {
    expect(aParametrosTurnosFijos(5, FILTROS_TURNOS_FIJOS_INICIALES, 1)).toEqual({ complejo: 5, page: 1 });
  });

  test('el lunes (día 0) viaja como filtro', () => {
    const filtros = { cancha: '8', estado: '2', dia: '0' };

    expect(aParametrosTurnosFijos(5, filtros, 3)).toEqual({
      complejo: 5, page: 3, cancha: '8', estado: '2', dia_semana: '0',
    });
  });
});

describe('aParametrosEnEspera', () => {
  test('pide los turnos con fechas en espera', () => {
    expect(aParametrosEnEspera(5, 2)).toEqual({ complejo: 5, en_espera: true, page: 2 });
  });
});

describe('validarTurnoFijo', () => {
  const valido = {
    ...VALORES_TURNO_FIJO_INICIALES,
    cancha: '3',
    dia_semana: '0',
    hora_inicio: '20:00',
    fecha_inicio_vigencia: '2026-11-16',
    nombre_cliente_manual: 'Cliente de muestra',
  };

  test('un turno fijo sin fecha de fin es válido', () => {
    expect(validarTurnoFijo(valido, HOY)).toEqual({});
  });

  test('exige los campos obligatorios; el lunes (0) cuenta como día elegido', () => {
    expect(Object.keys(validarTurnoFijo(VALORES_TURNO_FIJO_INICIALES, HOY)).sort()).toEqual([
      'cancha', 'dia_semana', 'fecha_inicio_vigencia', 'hora_inicio', 'nombre_cliente_manual',
    ]);
    expect(validarTurnoFijo(valido, HOY)).not.toHaveProperty('dia_semana');
  });

  test('la vigencia no puede empezar en el pasado ni terminar antes de empezar', () => {
    expect(validarTurnoFijo({ ...valido, fecha_inicio_vigencia: '2026-11-11' }, HOY)).toHaveProperty('fecha_inicio_vigencia');
    expect(validarTurnoFijo({ ...valido, fecha_fin_vigencia: '2026-11-15' }, HOY)).toHaveProperty('fecha_fin_vigencia');
    expect(validarTurnoFijo({ ...valido, fecha_fin_vigencia: '2026-12-14' }, HOY)).toEqual({});
  });
});

describe('cuerpoTurnoFijo', () => {
  const valores = {
    cancha: '3',
    dia_semana: '0',
    hora_inicio: '20:00',
    fecha_inicio_vigencia: '2026-11-16',
    fecha_fin_vigencia: '',
    nombre_cliente_manual: ' Cliente de muestra ',
    telefono_cliente_manual: '',
  };

  test('sin fecha de fin viaja nula y los números salen como números', () => {
    expect(cuerpoTurnoFijo(valores)).toEqual({
      cancha: 3,
      dia_semana: 0,
      hora_inicio: '20:00',
      fecha_inicio_vigencia: '2026-11-16',
      fecha_fin_vigencia: null,
      nombre_cliente_manual: 'Cliente de muestra',
      telefono_cliente_manual: '',
    });
  });
});

describe('proximasFechasDeTurnoFijo', () => {
  // 12/11/2026 es jueves: el próximo lunes (día 0) es el 16/11.
  const lunes = { dia_semana: 0, fecha_inicio_vigencia: '2026-11-01', fecha_fin_vigencia: null };

  test('lista las fechas del día de la semana a partir de hoy, de a siete días', () => {
    expect(proximasFechasDeTurnoFijo(lunes, HOY, 3)).toEqual(['2026-11-16', '2026-11-23', '2026-11-30']);
  });

  test('respeta el inicio de la vigencia cuando es posterior a hoy', () => {
    expect(proximasFechasDeTurnoFijo({ ...lunes, fecha_inicio_vigencia: '2026-12-01' }, HOY, 2)).toEqual(['2026-12-07', '2026-12-14']);
  });

  test('se detiene en el fin de la vigencia', () => {
    expect(proximasFechasDeTurnoFijo({ ...lunes, fecha_fin_vigencia: '2026-11-25' }, HOY, 8)).toEqual(['2026-11-16', '2026-11-23']);
  });

  test('incluye hoy si cae en el día del turno y no devuelve nada si la vigencia ya terminó', () => {
    expect(proximasFechasDeTurnoFijo({ ...lunes, dia_semana: 3 }, HOY, 1)).toEqual([HOY]);
    expect(proximasFechasDeTurnoFijo({ ...lunes, fecha_fin_vigencia: '2026-11-10' }, HOY, 3)).toEqual([]);
  });

  test('el domingo es el día 6', () => {
    expect(proximasFechasDeTurnoFijo({ ...lunes, dia_semana: 6 }, HOY, 1)).toEqual(['2026-11-15']);
  });
});

describe('aFilasEnEspera', () => {
  test('genera una fila por cada fecha en espera de cada turno fijo', () => {
    const turnos = [
      { id: 1, fechas_en_espera: [{ fecha: '2026-11-16', motivo: 'Feriado' }, { fecha: '2026-11-23', motivo: 'Feriado' }] },
      { id: 2, fechas_en_espera: [{ fecha: '2026-11-16', motivo: 'Mantenimiento' }] },
      { id: 3, fechas_en_espera: [] },
      { id: 4 },
    ];

    const filas = aFilasEnEspera(turnos);

    expect(filas.map((fila) => fila.clave)).toEqual(['1:2026-11-16', '1:2026-11-23', '2:2026-11-16']);
    expect(filas[2]).toMatchObject({ fecha: '2026-11-16', motivo: 'Mantenimiento', turno: { id: 2 } });
  });
});

describe('bloquesDeHorarios', () => {
  const rango = (dia, apertura, cierre, precio = null) => ({
    dia_semana: dia, hora_apertura: apertura, hora_cierre: cierre, precio_diferenciado: precio,
  });

  test('parte el rango en turnos consecutivos desde la apertura', () => {
    const bloques = bloquesDeHorarios([rango(0, '18:00:00', '21:00:00')], 0, 60, '38000.00');

    expect(bloques.map((bloque) => `${bloque.hora_inicio}-${bloque.hora_fin}`)).toEqual([
      '18:00-19:00', '19:00-20:00', '20:00-21:00',
    ]);
    expect(bloques[0].precio).toBe('38000.00');
  });

  test('con turnos de 90 minutos el resto que no completa un turno no se ofrece', () => {
    const bloques = bloquesDeHorarios([rango(2, '18:00:00', '21:30:00')], 2, 90);

    expect(bloques.map((bloque) => bloque.hora_inicio)).toEqual(['18:00', '19:30']);
  });

  test('cada rango genera sus turnos por separado y el resultado sale ordenado', () => {
    const rangos = [rango(1, '17:00:00', '19:00:00', '45000.00'), rango(1, '09:00:00', '11:00:00')];

    const bloques = bloquesDeHorarios(rangos, 1, 120, '30000.00');

    expect(bloques).toEqual([
      { hora_inicio: '09:00', hora_fin: '11:00', precio: '30000.00' },
      { hora_inicio: '17:00', hora_fin: '19:00', precio: '45000.00' },
    ]);
  });

  test('solo cuenta los rangos del día pedido; el lunes es el día 0', () => {
    const rangos = [rango(0, '18:00', '20:00'), rango(1, '18:00', '20:00')];

    expect(bloquesDeHorarios(rangos, 0, 60)).toHaveLength(2);
    expect(bloquesDeHorarios(rangos, '1', 60)).toHaveLength(2);
    expect(bloquesDeHorarios(rangos, 5, 60)).toEqual([]);
  });

  test('un rango más corto que el turno, una duración inválida o datos ausentes no dan bloques', () => {
    expect(bloquesDeHorarios([rango(0, '18:00', '18:45')], 0, 60)).toEqual([]);
    expect(bloquesDeHorarios([rango(0, '18:00', '20:00')], 0, 0)).toEqual([]);
    expect(bloquesDeHorarios([rango(0, '18:00', '20:00')], 0, undefined)).toEqual([]);
    expect(bloquesDeHorarios(undefined, 0, 60)).toEqual([]);
  });
});
