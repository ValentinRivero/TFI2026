import { describe, expect, test } from 'vitest';
import { describir, ESTADO_PAGO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import {
  aCentavos,
  ACCION_COBRO,
  accionesDeCobro,
  calcularDesglose,
  debeAbonarSena,
  errorDeAlias,
  esPorcentajeSenaValido,
  estadoDePago,
  estadoDeReserva,
  estadoReflejaElPago,
  exigeSena,
  filasDeDesglose,
  filasDeReserva,
  muestraSeguimientoDePago,
  normalizarAlias,
  tieneSena,
  validarSena,
} from './pagos.js';

describe('alias de transferencia', () => {
  test('se normaliza a mayúsculas y sin espacios en los extremos', () => {
    expect(normalizarAlias('  yacare.demo-sena ')).toBe('YACARE.DEMO-SENA');
    expect(normalizarAlias(null)).toBe('');
  });

  test.each(['YACARE.SENA', 'abc123', 'a-b.c-d', 'A'.repeat(20)])('acepta %s', (alias) => {
    expect(errorDeAlias(alias)).toBeUndefined();
  });

  test.each(['corto', 'A'.repeat(21), 'con espacio', 'ñandu.pago', 'alias_bajo', 'ali@s.mp', '<b>alias</b>'])(
    'rechaza %s',
    (alias) => {
      expect(errorDeAlias(alias)).toBe(t('configuracion.errorAlias', { minimo: 6, maximo: 20 }));
    },
  );

  test('vacío es válido salvo que se exija', () => {
    expect(errorDeAlias('')).toBeUndefined();
    expect(errorDeAlias('   ')).toBeUndefined();
    expect(errorDeAlias('', { obligatorio: true })).toBe(t('configuracion.errorAliasObligatorio'));
  });
});

describe('porcentaje de seña', () => {
  test.each(['0', '1', '30', '100', ' 50 '])('acepta %s', (valor) => {
    expect(esPorcentajeSenaValido(valor)).toBe(true);
  });

  test.each(['', '-1', '101', '12.5', 'treinta', '1e2', '+5'])('rechaza %s', (valor) => {
    expect(esPorcentajeSenaValido(valor)).toBe(false);
  });
});

describe('validarSena', () => {
  test('sin seña no exige alias', () => {
    expect(validarSena({ porcentaje_sena: '0', alias_transferencia: '' })).toEqual({});
  });

  test('con seña mayor a cero el alias es obligatorio', () => {
    expect(validarSena({ porcentaje_sena: '30', alias_transferencia: '' })).toEqual({
      alias_transferencia: t('configuracion.errorAliasObligatorio'),
    });
  });

  test('informa porcentaje y alias inválidos a la vez', () => {
    const errores = validarSena({ porcentaje_sena: '150', alias_transferencia: 'con espacio' });

    expect(Object.keys(errores)).toEqual(['porcentaje_sena', 'alias_transferencia']);
  });

  test('un alias válido con seña no tiene errores', () => {
    expect(validarSena({ porcentaje_sena: '30', alias_transferencia: 'yacare.sena' })).toEqual({});
  });
});

describe('cálculo de la seña', () => {
  test('convierte importes a centavos sin errores de coma flotante', () => {
    expect(aCentavos('38000.00')).toBe(3800000);
    expect(aCentavos('100.05')).toBe(10005);
    expect(aCentavos(19999.99)).toBe(1999999);
  });

  test.each([
    ['38000.00', 30, 11400, 26600],
    ['38000.00', 0, 0, 38000],
    ['38000.00', 100, 38000, 0],
    ['1000.00', 33, 330, 670],
    ['100.05', 50, 50.03, 50.02],
    ['100.01', 50, 50.01, 50],
    ['0.01', 50, 0.01, 0],
    ['45000.50', 30, 13500.15, 31500.35],
    ['19999.99', 15, 3000, 16999.99],
    ['33333.33', 7, 2333.33, 31000],
  ])('precio %s con %i%% deja seña %d y saldo %d', (precio, porcentaje, sena, saldo) => {
    const desglose = calcularDesglose(precio, porcentaje);

    expect(desglose.sena).toBeCloseTo(sena, 2);
    expect(desglose.saldo).toBeCloseTo(saldo, 2);
    expect(desglose.sena + desglose.saldo).toBeCloseTo(Number(precio), 2);
  });

  test('un porcentaje inválido no suma seña', () => {
    expect(calcularDesglose('38000.00', 'x').sena).toBe(0);
    expect(calcularDesglose('38000.00', -5).sena).toBe(0);
    expect(calcularDesglose('38000.00', undefined).saldo).toBe(38000);
  });

  test('un porcentaje por encima del máximo se acota a 100', () => {
    expect(calcularDesglose('1000.00', 250).sena).toBe(1000);
  });

  test('el complejo exige seña con un porcentaje mayor a cero', () => {
    expect(exigeSena({ porcentaje_sena: 30 })).toBe(true);
    expect(exigeSena({ porcentaje_sena: 0 })).toBe(false);
    expect(exigeSena({})).toBe(false);
    expect(exigeSena(null)).toBe(false);
  });
});

describe('filas de montos', () => {
  test('el desglose previo muestra precio, seña y saldo', () => {
    const filas = filasDeDesglose({ total: 38000, sena: 11400, saldo: 26600 });

    expect(filas.map((fila) => fila.clave)).toEqual(['total', 'sena', 'saldo']);
    expect(filas.find((fila) => fila.clave === 'sena').destacada).toBe(true);
  });

  test('una reserva con seña muestra seña, abonado y saldo', () => {
    const filas = filasDeReserva({ precio_acordado: '38000.00', monto_sena: '11400.00', monto_pagado: '0.00', saldo_restante: '38000.00' });

    expect(filas.map((fila) => fila.clave)).toEqual(['total', 'sena', 'pagado', 'saldo']);
  });

  test('sin seña acordada omite la fila de seña', () => {
    const filas = filasDeReserva({ precio_acordado: '38000.00', monto_sena: '0.00', monto_pagado: '38000.00', saldo_restante: '0.00' });

    expect(filas.map((fila) => fila.clave)).toEqual(['total', 'pagado', 'saldo']);
  });
});

describe('estado de pago', () => {
  test.each([
    [1, 'Sin seña', 'badge-neutro'],
    [2, 'Seña pendiente', 'badge-aviso'],
    [3, 'Seña abonada', 'badge-info'],
    [4, 'Pagada', 'badge-ok'],
  ])('el código %i es %s', (codigo, etiqueta, badge) => {
    expect(describir(ESTADO_PAGO, codigo)).toEqual({ etiqueta, badge });
    expect(estadoDePago({ estado_pago: codigo })).toEqual({ etiqueta, badge });
  });

  test('un código desconocido se muestra como sin seña', () => {
    expect(estadoDePago({ estado_pago: 99 }).etiqueta).toBe('Sin seña');
  });

  test('muestra el seguimiento cuando hay seña acordada o algo abonado', () => {
    expect(muestraSeguimientoDePago({ estado: 1, monto_sena: '11400.00', monto_pagado: '0.00' })).toBe(true);
    expect(muestraSeguimientoDePago({ estado: 3, monto_sena: '0.00', monto_pagado: '38000.00' })).toBe(true);
    expect(muestraSeguimientoDePago({ estado: 1, monto_sena: '0.00', monto_pagado: '0.00' })).toBe(false);
  });

  test('una cancelada sin nada abonado no tiene seguimiento; con una seña abonada sí', () => {
    expect(muestraSeguimientoDePago({ estado: 4, monto_sena: '11400.00', monto_pagado: '0.00' })).toBe(false);
    expect(muestraSeguimientoDePago({ estado: 5, monto_sena: '11400.00', monto_pagado: '11400.00' })).toBe(true);
  });

  test('el jugador debe abonar la seña solo si el servidor entregó el alias', () => {
    expect(debeAbonarSena({ datos_transferencia: { alias: 'YACARE.SENA', titular: '' } })).toBe(true);
    expect(debeAbonarSena({ datos_transferencia: null })).toBe(false);
    expect(debeAbonarSena({})).toBe(false);
  });

  test('las acciones de cobro salen de lo que admite el servidor', () => {
    expect(accionesDeCobro({ puede_confirmar_sena: true, puede_registrar_pago: true })).toEqual([ACCION_COBRO.SENA, ACCION_COBRO.PAGO_TOTAL]);
    expect(accionesDeCobro({ puede_confirmar_sena: false, puede_registrar_pago: true })).toEqual([ACCION_COBRO.PAGO_TOTAL]);
    expect(accionesDeCobro({ puede_confirmar_sena: false, puede_registrar_pago: false })).toEqual([]);
    expect(accionesDeCobro({})).toEqual([]);
  });
});

describe('estado de la reserva en pantalla', () => {
  const senada = (estadoPago, montoSena = '11400.00') => ({ estado: 3, estado_pago: estadoPago, monto_sena: montoSena });

  test('tiene seña cuando hay un monto de seña acordado', () => {
    expect(tieneSena({ monto_sena: '11400.00' })).toBe(true);
    expect(tieneSena({ monto_sena: '0.00' })).toBe(false);
    expect(tieneSena({})).toBe(false);
  });

  test('una señada muestra su estado de pago en lugar de «Señada o pagada»', () => {
    expect(estadoDeReserva(senada(3))).toEqual({ etiqueta: 'Seña abonada', badge: 'badge-info' });
    expect(estadoDeReserva(senada(4))).toEqual({ etiqueta: 'Pagada', badge: 'badge-ok' });
    expect(estadoReflejaElPago(senada(3))).toBe(true);
    expect(estadoReflejaElPago(senada(4))).toBe(true);
  });

  test('una señada antigua sin montos conserva la etiqueta original', () => {
    expect(estadoDeReserva(senada(1, '0.00')).etiqueta).toBe('Señada o pagada');
    expect(estadoReflejaElPago(senada(1, '0.00'))).toBe(false);
  });

  test('una pendiente sin seña se llama «Pendiente» y con seña «Pendiente de seña»', () => {
    expect(estadoDeReserva({ estado: 1, monto_sena: '0.00' }).etiqueta).toBe('Pendiente');
    expect(estadoDeReserva({ estado: 1, monto_sena: '11400.00' }).etiqueta).toBe('Pendiente de seña');
  });

  test('el resto de los estados usa su etiqueta, también si están pagos', () => {
    expect(estadoDeReserva({ estado: 2, monto_sena: '0.00', estado_pago: 4 }).etiqueta).toBe('Confirmada');
    expect(estadoDeReserva({ estado: 7, monto_sena: '11400.00', estado_pago: 4 }).etiqueta).toBe('Completada');
    expect(estadoReflejaElPago({ estado: 2, estado_pago: 4 })).toBe(false);
  });

  test('un estado desconocido cae a la baja', () => {
    expect(estadoDeReserva({ estado: 99, monto_sena: '0.00' }).etiqueta).toBe('Baja');
  });
});
