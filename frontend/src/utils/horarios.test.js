import { describe, expect, test } from 'vitest';
import { agruparPorDia, aFilaBorrador, calcularCambios, filaNueva, hayCambios, validarBorrador } from './horarios.js';

const servidor = [
  { id: 1, dia_semana: 0, hora_apertura: '09:00:00', hora_cierre: '13:00:00', precio_diferenciado: null },
  { id: 2, dia_semana: 0, hora_apertura: '16:00:00', hora_cierre: '23:00:00', precio_diferenciado: '45000.00' },
];
const base = servidor.map(aFilaBorrador);

describe('aFilaBorrador', () => {
  test('normaliza horas y precio del servidor', () => {
    expect(base[0]).toMatchObject({ id: 1, hora_apertura: '09:00', hora_cierre: '13:00', precio_diferenciado: '' });
    expect(base[1].precio_diferenciado).toBe('45000');
  });
});

describe('agruparPorDia', () => {
  test('devuelve los siete días y ordena cada uno por apertura', () => {
    const grupos = agruparPorDia([base[1], base[0], filaNueva(3, 'n1')]);

    expect(grupos).toHaveLength(7);
    expect(grupos[0].filas.map((fila) => fila.id)).toEqual([1, 2]);
    expect(grupos[3].filas).toHaveLength(1);
    expect(grupos[6].filas).toEqual([]);
  });
});

describe('validarBorrador', () => {
  test('un borrador correcto no tiene errores', () => {
    expect(validarBorrador(base)).toEqual({});
  });

  test('exige ambas horas y un cierre posterior a la apertura', () => {
    const errores = validarBorrador([filaNueva(1, 'a'), { ...filaNueva(1, 'b'), hora_apertura: '10:00', hora_cierre: '09:00' }]);

    expect(errores.a.hora_apertura).toBeTruthy();
    expect(errores.a.hora_cierre).toBeTruthy();
    expect(errores.b.hora_cierre).toBeTruthy();
  });

  test('detecta rangos superpuestos del mismo día pero no los de días distintos', () => {
    const superpuesto = { ...filaNueva(0, 'x'), hora_apertura: '12:00', hora_cierre: '14:00' };
    const otroDia = { ...filaNueva(1, 'y'), hora_apertura: '12:00', hora_cierre: '14:00' };

    const errores = validarBorrador([...base, superpuesto, otroDia]);

    expect(errores.x.hora_apertura).toBeTruthy();
    expect(errores.y).toBeUndefined();
  });

  test('el rango que arranca antes de que termine el anterior queda marcado', () => {
    const solapado = { ...filaNueva(0, 'x'), hora_apertura: '14:00', hora_cierre: '17:00' };

    const errores = validarBorrador([...base, solapado]);

    expect(errores['h-2'].hora_apertura).toBeTruthy();
    expect(errores.x).toBeUndefined();
  });

  test('rangos contiguos no se consideran superpuestos', () => {
    const contiguo = { ...filaNueva(0, 'c'), hora_apertura: '13:00', hora_cierre: '16:00' };

    expect(validarBorrador([...base, contiguo])).toEqual({});
  });

  test('rechaza un precio negativo o no numérico', () => {
    const negativo = { ...base[0], precio_diferenciado: '-5' };
    const texto = { ...base[1], precio_diferenciado: 'abc' };

    const errores = validarBorrador([negativo, texto]);

    expect(errores['h-1'].precio_diferenciado).toBeTruthy();
    expect(errores['h-2'].precio_diferenciado).toBeTruthy();
  });
});

describe('calcularCambios', () => {
  test('sin diferencias no hay cambios', () => {
    expect(hayCambios(calcularCambios(base, base.map((fila) => ({ ...fila }))))).toBe(false);
  });

  test('una fila ausente del borrador es una baja', () => {
    expect(calcularCambios(base, [base[0]]).bajas).toEqual([2]);
  });

  test('solo viajan los campos modificados y un precio vacío pasa a null', () => {
    const borrador = [{ ...base[0], hora_cierre: '14:00', precio_diferenciado: '30000' }, { ...base[1], precio_diferenciado: '' }];

    const { modificaciones } = calcularCambios(base, borrador);

    expect(modificaciones).toEqual([
      { id: 1, cambios: { hora_cierre: '14:00', precio_diferenciado: '30000' } },
      { id: 2, cambios: { precio_diferenciado: null } },
    ]);
  });

  test('un precio equivalente escrito distinto no cuenta como cambio', () => {
    const borrador = [base[0], { ...base[1], precio_diferenciado: '45000.00' }];

    expect(calcularCambios(base, borrador).modificaciones).toEqual([]);
  });

  test('una fila nueva es un alta y omite el precio si no es diferenciado', () => {
    const nueva = { ...filaNueva(4, 'n'), hora_apertura: '10:00', hora_cierre: '12:00' };
    const conPrecio = { ...nueva, clave: 'm', precio_diferenciado: '5000' };

    const { altas } = calcularCambios(base, [...base, nueva, conPrecio]);

    expect(altas[0]).toEqual({ dia_semana: 4, hora_apertura: '10:00', hora_cierre: '12:00' });
    expect(altas[1].precio_diferenciado).toBe('5000');
  });
});
