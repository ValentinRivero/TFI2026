import { describe, expect, test } from 'vitest';
import { describir, ESTADO_PAGO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import {
  aCentavos,
  ACCION_COBRO,
  accionesDeCobro,
  calcularDesglose,
  colapsarEspacios,
  cuerpoTransferencia,
  debeAbonarSena,
  errorDeAlias,
  errorDeCbu,
  errorDeNotaRechazo,
  errorDeReferenciaTransferencia,
  errorDeTitularTransferencia,
  esCbuValido,
  esPorcentajeSenaValido,
  estadoDePago,
  estadoDeReserva,
  estadoReflejaElPago,
  etiquetaDeEstadoDestino,
  exigeSena,
  filasDeDesglose,
  filasDeReserva,
  muestraSeguimientoDePago,
  normalizarAlias,
  normalizarCbu,
  senaConfirmada,
  tieneSena,
  transferenciaParaRevisar,
  transferenciaRechazada,
  validarSena,
  validarTransferencia,
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

describe('aviso de transferencia', () => {
  test('colapsa los espacios de los extremos y los repetidos', () => {
    expect(colapsarEspacios('  María   José \t Pérez ')).toBe('María José Pérez');
    expect(colapsarEspacios(null)).toBe('');
  });

  test.each(['Marta López', 'María José Pérez', "O'Brien-Díaz Jr.", 'Pérez & Hijos S.A.', 'Ñandú 2 S.R.L.', '  Ana   Gómez '])(
    'acepta el nombre %s',
    (titular) => {
      expect(errorDeTitularTransferencia(titular)).toBeUndefined();
    },
  );

  test.each(['', '   ', 'A', '12', '1 2', '<b>Marta</b>', 'Marta; DROP TABLE', 'x'.repeat(101), 'Ana\u0000'])(
    'rechaza el nombre %j',
    (titular) => {
      expect(errorDeTitularTransferencia(titular)).toBe(t('transferencia.errorTitular', { minimo: 2, maximo: 100 }));
    },
  );

  test.each(['ABC', 'OP-48213', '0012345678', 'A1.B2_C3/D4-E5', 'x'.repeat(60), '  OP-1234  '])('acepta la operación %s', (referencia) => {
    expect(errorDeReferenciaTransferencia(referencia)).toBeUndefined();
  });

  test.each(['', 'ab', 'con espacio', 'x'.repeat(61), '-OP123', '../etc/passwd', '<script>', 'OP;123', 'OP 123'])(
    'rechaza la operación %j',
    (referencia) => {
      expect(errorDeReferenciaTransferencia(referencia)).toBe(t('transferencia.errorReferencia', { minimo: 3, maximo: 60 }));
    },
  );

  test('valida los dos campos y devuelve un error por cada uno', () => {
    expect(validarTransferencia({ titular: 'Marta López', referencia: 'OP-48213' })).toEqual({});
    expect(Object.keys(validarTransferencia({ titular: '', referencia: '' }))).toEqual(['titular', 'referencia']);
    expect(Object.keys(validarTransferencia({ titular: 'Marta López', referencia: 'a b' }))).toEqual(['referencia']);
  });

  test('el cuerpo viaja con los espacios colapsados y sin campos de más', () => {
    expect(cuerpoTransferencia({ titular: '  Marta   López ', referencia: ' OP-1 2 ', reserva: { id: 1 } })).toEqual({
      titular: 'Marta López',
      referencia: 'OP-1 2',
    });
  });

  test('el personal revisa una transferencia informada mientras la seña sigue sin confirmarse', () => {
    expect(transferenciaParaRevisar({ transferencia_informada: true, puede_confirmar_sena: true })).toBe(true);
    expect(transferenciaParaRevisar({ transferencia_informada: true, puede_confirmar_sena: false })).toBe(false);
    expect(transferenciaParaRevisar({ transferencia_informada: false, puede_confirmar_sena: true })).toBe(false);
    expect(transferenciaParaRevisar({})).toBe(false);
  });
});

describe('CBU o CVU', () => {
  // Banco 000 inexistente, con los dígitos verificadores correctos: no corresponde a ninguna cuenta real.
  const CBU = '0000000000000000123459';

  test('se normaliza quitando espacios y guiones', () => {
    expect(normalizarCbu(' 0000 0000-0000 0000-1234 59 ')).toBe(CBU);
    expect(normalizarCbu(null)).toBe('');
  });

  test.each([CBU, '0000 0000-0000 0000-1234 59', '2850590940090418135201', '0170099220000067797370'])('acepta %s', (cbu) => {
    expect(esCbuValido(cbu)).toBe(true);
    expect(errorDeCbu(cbu)).toBeUndefined();
  });

  test('vacío es válido: el CBU es opcional', () => {
    expect(errorDeCbu('')).toBeUndefined();
    expect(errorDeCbu('   ')).toBeUndefined();
  });

  test.each(['123', '000000000000000012345', '00000000000000001234590', '00000000000000001234AB', 'x'.repeat(22)])(
    'un largo o caracteres incorrectos (%s) informa el largo',
    (cbu) => {
      expect(errorDeCbu(cbu)).toBe(t('configuracion.errorCbuLargo', { largo: 22 }));
    },
  );

  test.each(['2850590940090418135202', '2850590940090418135211', '2851590940090418135201', '0000000000000000123450'])(
    'un dígito verificador que no coincide (%s) lo rechaza',
    (cbu) => {
      expect(esCbuValido(cbu)).toBe(false);
      expect(errorDeCbu(cbu)).toBe(t('configuracion.errorCbuVerificador'));
    },
  );

  test('la sección de seña valida el CBU aunque no se exija seña', () => {
    expect(validarSena({ porcentaje_sena: '0', alias_transferencia: '', cbu_cvu_transferencia: CBU })).toEqual({});
    expect(Object.keys(validarSena({ porcentaje_sena: '0', alias_transferencia: '', cbu_cvu_transferencia: '123' }))).toEqual([
      'cbu_cvu_transferencia',
    ]);
  });
});

describe('estado pendiente con la seña ya abonada y destinos de un cambio de estado', () => {
  test('pendiente con la seña ya abonada es simplemente «Pendiente»', () => {
    const reserva = { estado: 1, monto_sena: '11400.00', monto_pagado: '11400.00' };

    expect(estadoDeReserva(reserva).etiqueta).toBe('Pendiente');
  });

  test('pendiente con la seña a medio abonar sigue pendiente de seña', () => {
    expect(estadoDeReserva({ estado: 1, monto_sena: '11400.00', monto_pagado: '5000.00' }).etiqueta).toBe('Pendiente de seña');
  });

  test('el destino «pendiente» se rotula según haya una seña por abonar', () => {
    expect(etiquetaDeEstadoDestino({ estado: 2, monto_sena: '11400.00', monto_pagado: '0.00' }, 1)).toBe('Pendiente de seña');
    expect(etiquetaDeEstadoDestino({ estado: 3, monto_sena: '11400.00', monto_pagado: '11400.00' }, 1)).toBe('Pendiente');
    expect(etiquetaDeEstadoDestino({ estado: 2, monto_sena: '0.00', monto_pagado: '0.00' }, 1)).toBe('Pendiente');
  });

  test('los demás destinos conservan su etiqueta', () => {
    const reserva = { estado: 1, monto_sena: '11400.00', monto_pagado: '0.00', estado_pago: 2 };

    expect(etiquetaDeEstadoDestino(reserva, 2)).toBe('Confirmada');
    expect(etiquetaDeEstadoDestino(reserva, 3)).toBe('Señada o pagada');
  });

  test('la seña está confirmada cuando el pago es seña abonada o pagada', () => {
    expect(senaConfirmada({ estado_pago: 3 })).toBe(true);
    expect(senaConfirmada({ estado_pago: 4 })).toBe(true);
    expect(senaConfirmada({ estado_pago: 2 })).toBe(false);
    expect(senaConfirmada({ estado_pago: 1 })).toBe(false);
    expect(senaConfirmada({})).toBe(false);
  });
});

describe('rechazo de la transferencia informada', () => {
  const informada = { transferencia_informada: true, puede_confirmar_sena: true };

  test('una transferencia rechazada ya no está para revisar y se marca como rechazada', () => {
    const rechazada = { ...informada, transferencia_rechazada: true };

    expect(transferenciaParaRevisar(rechazada)).toBe(false);
    expect(transferenciaRechazada(rechazada)).toBe(true);
  });

  test('una informada sin rechazo sigue para revisar y no figura como rechazada', () => {
    expect(transferenciaParaRevisar(informada)).toBe(true);
    expect(transferenciaRechazada(informada)).toBe(false);
  });

  test('sin transferencia informada no hay nada que revisar ni rechazar', () => {
    expect(transferenciaParaRevisar({ puede_confirmar_sena: true })).toBe(false);
    expect(transferenciaRechazada({ transferencia_rechazada: true })).toBe(false);
  });

  test('la nota del rechazo admite hasta 120 caracteres y puede quedar vacía', () => {
    expect(errorDeNotaRechazo('')).toBeUndefined();
    expect(errorDeNotaRechazo('x'.repeat(120))).toBeUndefined();
    expect(errorDeNotaRechazo(`  ${'x'.repeat(120)}  `)).toBeUndefined();
    expect(errorDeNotaRechazo('x'.repeat(121))).toBe('La nota no puede superar los 120 caracteres.');
  });
});
