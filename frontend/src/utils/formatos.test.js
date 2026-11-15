import { describe, expect, test } from 'vitest';
import {
  aFechaIso,
  aFechaVisible,
  desdeFechaVisible,
  enmascararFecha,
  diasEntre,
  formatearEntero,
  formatearFechaHora,
  formatearPorcentaje,
  formatearFechaCorta,
  formatearDiaCorto,
  formatearFechaLarga,
  formatearHora,
  formatearMomento,
  formatearPrecio,
  formatearTemperatura,
  parsearFecha,
  sumarDias,
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
    expect(formatearFechaLarga('2026-11-18')).toMatch(/^Miércoles,? 18 de noviembre$/);
  });

  test('solo la primera letra va en mayúscula: la preposición y el mes quedan en minúscula', () => {
    expect(formatearFechaLarga('2026-11-12')).toMatch(/^Jueves,? 12 de noviembre$/);
    expect(formatearFechaLarga('2026-03-01')).toMatch(/^Domingo,? 1 de marzo$/);
  });

  test('fecha corta día/mes/año', () => {
    expect(formatearFechaCorta('2026-11-08')).toBe('08/11/2026');
  });

  test('una fecha inválida devuelve texto vacío', () => {
    expect(formatearFechaLarga('2026-02-30')).toBe('');
    expect(formatearFechaCorta('mañana')).toBe('');
  });
});

describe('formatearMomento', () => {
  test('muestra día, mes y hora en hora local', () => {
    const texto = normalizar(formatearMomento(new Date(2026, 10, 24, 16, 5).toISOString()));

    expect(texto).toMatch(/24 de noviembre/);
    expect(texto).toContain('16:05');
  });

  test('un texto que no es un instante da texto vacío', () => {
    expect(formatearMomento('')).toBe('');
    expect(formatearMomento('mañana')).toBe('');
  });
});

describe('sumarDias', () => {
  test('suma y resta días cruzando mes y año', () => {
    expect(sumarDias('2026-11-30', 1)).toBe('2026-12-01');
    expect(sumarDias('2026-12-31', 1)).toBe('2027-01-01');
    expect(sumarDias('2026-03-01', -1)).toBe('2026-02-28');
  });

  test('una fecha inválida devuelve null', () => {
    expect(sumarDias('2026-13-01', 1)).toBeNull();
    expect(sumarDias('', 1)).toBeNull();
  });
});

describe('formatearTemperatura', () => {
  test('redondea y agrega el grado', () => {
    expect(formatearTemperatura(18.6)).toBe('19°');
    expect(formatearTemperatura(-0.4)).toBe('0°');
  });

  test('un valor que no es número da texto vacío', () => {
    expect(formatearTemperatura(null)).toBe('');
    expect(formatearTemperatura(Number.NaN)).toBe('');
  });
});

describe('formatearDiaCorto', () => {
  test('arma día de la semana y número sin correr el día', () => {
    expect(normalizar(formatearDiaCorto('2026-11-18'))).toMatch(/18/);
    expect(normalizar(formatearDiaCorto('2026-11-18'))).toMatch(/^Mié/);
  });

  test('una fecha inválida da texto vacío', () => {
    expect(formatearDiaCorto('2026-13-40')).toBe('');
  });
});

describe('diasEntre', () => {
  test('cuenta los días entre dos fechas de calendario', () => {
    expect(diasEntre('2026-11-12', '2026-11-12')).toBe(0);
    expect(diasEntre('2026-11-01', '2026-11-30')).toBe(29);
    expect(diasEntre('2026-01-01', '2027-01-01')).toBe(365);
    expect(diasEntre('2026-11-12', '2026-11-10')).toBe(-2);
  });

  test('una fecha inexistente da null', () => {
    expect(diasEntre('2026-02-31', '2026-03-01')).toBeNull();
    expect(diasEntre('', '2026-03-01')).toBeNull();
  });
});

describe('formatearEntero y formatearPorcentaje', () => {
  test('el entero lleva separador de miles', () => {
    expect(normalizar(formatearEntero(1254))).toBe('1.254');
    expect(formatearEntero(0)).toBe('0');
    expect(formatearEntero('30')).toBe('30');
  });

  test('un valor ausente o inválido da texto vacío', () => {
    expect(formatearEntero(null)).toBe('');
    expect(formatearEntero('')).toBe('');
    expect(formatearEntero('abc')).toBe('');
  });

  test('el porcentaje lleva hasta un decimal y el símbolo', () => {
    expect(normalizar(formatearPorcentaje(50))).toBe('50 %');
    expect(normalizar(formatearPorcentaje(12.34))).toBe('12,3 %');
    expect(formatearPorcentaje(null)).toBe('');
  });
});

describe('formatearFechaHora', () => {
  test('muestra día, mes, año y hora en hora local', () => {
    expect(normalizar(formatearFechaHora('2026-11-24T16:00:00-03:00'))).toMatch(/^\d{2}\/\d{2}\/2026,? \d{2}:\d{2}$/);
  });

  test('un valor vacío o inválido da texto vacío', () => {
    expect(formatearFechaHora('')).toBe('');
    expect(formatearFechaHora('no es una fecha')).toBe('');
    expect(formatearFechaHora(null)).toBe('');
  });
});

describe('fecha visible dd/mm/aaaa', () => {
  test('la fecha corta siempre se arma como día, mes y año', () => {
    expect(aFechaVisible('2026-11-12')).toBe('12/11/2026');
    expect(aFechaVisible('2026-01-05')).toBe('05/01/2026');
    expect(formatearFechaCorta('2026-12-31')).toBe('31/12/2026');
  });

  test('una fecha inexistente o vacía da texto vacío', () => {
    expect(aFechaVisible('2026-02-31')).toBe('');
    expect(aFechaVisible('')).toBe('');
    expect(aFechaVisible(null)).toBe('');
  });

  test('la máscara agrega las barras y descarta lo que no es un dígito', () => {
    expect(enmascararFecha('1')).toBe('1');
    expect(enmascararFecha('121')).toBe('12/1');
    expect(enmascararFecha('12112026')).toBe('12/11/2026');
    expect(enmascararFecha('12-11-2026')).toBe('12/11/2026');
    expect(enmascararFecha('12/11/20269999')).toBe('12/11/2026');
    expect(enmascararFecha('abc')).toBe('');
    expect(enmascararFecha(null)).toBe('');
  });

  test('desdeFechaVisible vuelve a AAAA-MM-DD solo con una fecha completa y real', () => {
    expect(desdeFechaVisible('12/11/2026')).toBe('2026-11-12');
    expect(desdeFechaVisible('29/02/2028')).toBe('2028-02-29');
    expect(desdeFechaVisible('29/02/2027')).toBeNull();
    expect(desdeFechaVisible('12/11/26')).toBeNull();
    expect(desdeFechaVisible('')).toBeNull();
  });

  test('ida y vuelta entre el valor de la API y el campo', () => {
    expect(desdeFechaVisible(aFechaVisible('2026-11-12'))).toBe('2026-11-12');
  });
});
