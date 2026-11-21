import { describe, expect, test } from 'vitest';
import {
  aParametrosAgenda,
  cambiosAlAlternarRango,
  cuerpoReservaManual,
  errorDeObservaciones,
  estadosDeReapertura,
  estadosSiguientes,
  fechaInicialDeAlta,
  filtrosAgendaIniciales,
  observacionesModificadas,
  periodoActivo,
  puedeCancelarElComplejo,
  puedeReabrir,
  rangoDelPeriodo,
  validarFiltrosAgenda,
  validarReservaManual,
  VALORES_RESERVA_MANUAL_INICIALES,
  vistaDeAgenda,
} from './agenda.js';

const HOY = '2026-11-12';
// Con seña acordada por defecto: sin ella la reserva no admite el estado «Señada».
const reserva = (estado, fecha = '2026-11-12', hora = '20:00:00', montoSena = '11400.00') => ({
  estado, fecha_turno: fecha, hora_inicio: hora, monto_sena: montoSena,
});
// Las 15:00 del 12/11 en hora local.
const AHORA = new Date(2026, 10, 12, 15, 0);

describe('aParametrosAgenda', () => {
  test('abre en el día de hoy para el complejo', () => {
    expect(aParametrosAgenda(5, filtrosAgendaIniciales(HOY), 1)).toEqual({ complejo: 5, page: 1, fecha: HOY });
  });

  test('suma los filtros activos con el nombre que usa la API', () => {
    const filtros = { fecha: '2026-11-20', cancha: '8', estado: '3', conConflicto: true };

    expect(aParametrosAgenda(5, filtros, 2)).toEqual({
      complejo: 5, page: 2, fecha: '2026-11-20', cancha: '8', estado: '3', con_conflicto: true,
    });
  });

  test('sin fecha o con una fecha inexistente lista todas las reservas', () => {
    expect(aParametrosAgenda(5, { ...filtrosAgendaIniciales(HOY), fecha: '' }, 1)).not.toHaveProperty('fecha');
    expect(aParametrosAgenda(5, { ...filtrosAgendaIniciales(HOY), fecha: '2026-02-31' }, 1)).not.toHaveProperty('fecha');
  });
});

describe('aParametrosAgenda con rango de fechas', () => {
  const conRango = (cambios) => ({ ...filtrosAgendaIniciales(HOY), conRango: true, ...cambios });

  test('envía fecha_desde y fecha_hasta y no la fecha de un solo día', () => {
    const params = aParametrosAgenda(5, conRango({ fecha: '2026-11-20', fecha_desde: '2026-10-14', fecha_hasta: HOY }), 1);

    expect(params).toEqual({ complejo: 5, page: 1, fecha_desde: '2026-10-14', fecha_hasta: HOY });
    expect(params).not.toHaveProperty('fecha');
  });

  test('sin rango activo ignora las fechas del rango', () => {
    const params = aParametrosAgenda(5, { ...filtrosAgendaIniciales(HOY), fecha_desde: '2026-10-14', fecha_hasta: HOY }, 1);

    expect(params).toEqual({ complejo: 5, page: 1, fecha: HOY });
  });

  test('abre en hoy hasta hoy y combina el rango con el resto de los filtros', () => {
    expect(aParametrosAgenda(5, conRango({ cancha: '8', estado: '3', conConflicto: true }), 2)).toEqual({
      complejo: 5, page: 2, fecha_desde: HOY, fecha_hasta: HOY, cancha: '8', estado: '3', con_conflicto: true,
    });
  });

  test('una fecha del rango vacía o inexistente no viaja', () => {
    const params = aParametrosAgenda(5, conRango({ fecha_desde: '', fecha_hasta: '2026-02-31' }), 1);

    expect(params).not.toHaveProperty('fecha_desde');
    expect(params).not.toHaveProperty('fecha_hasta');
  });
});

describe('validarFiltrosAgenda', () => {
  const conRango = (cambios) => ({ ...filtrosAgendaIniciales(HOY), conRango: true, ...cambios });

  test('sin rango activo no hay nada que validar, aunque las fechas guardadas estén al revés', () => {
    expect(validarFiltrosAgenda({ ...filtrosAgendaIniciales(HOY), fecha_desde: '2026-12-01', fecha_hasta: '2026-11-01' })).toEqual({});
  });

  test('hoy hasta hoy es válido, igual que un rango de varios días', () => {
    expect(validarFiltrosAgenda(conRango({}))).toEqual({});
    expect(validarFiltrosAgenda(conRango({ fecha_desde: '2026-10-14', fecha_hasta: HOY }))).toEqual({});
  });

  test('la fecha hasta no puede ser anterior a la fecha desde', () => {
    expect(validarFiltrosAgenda(conRango({ fecha_desde: '2026-11-20', fecha_hasta: '2026-11-19' }))).toEqual({
      fecha_hasta: 'La fecha hasta no puede ser anterior a la fecha desde.',
    });
  });

  test('pide una fecha válida cuando falta alguna y no compara el orden', () => {
    expect(validarFiltrosAgenda(conRango({ fecha_desde: '' }))).toEqual({ fecha_desde: 'Ingresá una fecha válida.' });
    expect(validarFiltrosAgenda(conRango({ fecha_hasta: '' }))).toEqual({ fecha_hasta: 'Ingresá una fecha válida.' });
    expect(Object.keys(validarFiltrosAgenda(conRango({ fecha_desde: '', fecha_hasta: '' })))).toEqual(['fecha_desde', 'fecha_hasta']);
  });

  test('el orden se compara por fecha de calendario, también entre meses y años', () => {
    expect(validarFiltrosAgenda(conRango({ fecha_desde: '2026-12-31', fecha_hasta: '2027-01-01' }))).toEqual({});
    expect(validarFiltrosAgenda(conRango({ fecha_desde: '2027-01-01', fecha_hasta: '2026-12-31' }))).toHaveProperty('fecha_hasta');
  });
});

describe('cambiosAlAlternarRango', () => {
  test('al activarlo parte del día que se estaba viendo', () => {
    expect(cambiosAlAlternarRango({ ...filtrosAgendaIniciales(HOY), fecha: '2026-11-20' }, true, HOY)).toEqual({
      conRango: true, fecha_desde: '2026-11-20', fecha_hasta: '2026-11-20',
    });
  });

  test('con los filtros de origen queda de hoy hasta hoy', () => {
    expect(cambiosAlAlternarRango(filtrosAgendaIniciales(HOY), true, HOY)).toEqual({
      conRango: true, fecha_desde: HOY, fecha_hasta: HOY,
    });
  });

  test('sin un día válido que conservar parte de hoy', () => {
    expect(cambiosAlAlternarRango({ ...filtrosAgendaIniciales(HOY), fecha: '' }, true, HOY)).toMatchObject({ fecha_desde: HOY, fecha_hasta: HOY });
  });

  test('al desactivarlo vuelve al día único con el inicio del rango', () => {
    const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, fecha_desde: '2026-10-14', fecha_hasta: HOY };

    expect(cambiosAlAlternarRango(filtros, false, HOY)).toEqual({ conRango: false, fecha: '2026-10-14' });
  });

  test('al desactivarlo con el inicio vacío vuelve a hoy', () => {
    const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, fecha_desde: '' };

    expect(cambiosAlAlternarRango(filtros, false, HOY)).toEqual({ conRango: false, fecha: HOY });
  });
});

describe('rangoDelPeriodo', () => {
  test.each([
    ['semana', '2026-11-06'],
    ['mes', '2026-10-14'],
    ['trimestre', '2026-08-15'],
  ])('%s termina hoy e incluye hoy', (periodo, desde) => {
    expect(rangoDelPeriodo(periodo, HOY)).toEqual({ fecha_desde: desde, fecha_hasta: HOY });
  });

  test('cruza el cambio de año', () => {
    expect(rangoDelPeriodo('mes', '2027-01-10')).toEqual({ fecha_desde: '2026-12-12', fecha_hasta: '2027-01-10' });
  });

  test('un período desconocido o vacío no da rango', () => {
    expect(rangoDelPeriodo('anio', HOY)).toBeNull();
    expect(rangoDelPeriodo('', HOY)).toBeNull();
  });

  test('el rango de cada período es válido para la consulta', () => {
    ['semana', 'mes', 'trimestre'].forEach((periodo) => {
      const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, ...rangoDelPeriodo(periodo, HOY) };
      expect(validarFiltrosAgenda(filtros)).toEqual({});
    });
  });
});

describe('periodoActivo', () => {
  test('reconoce el período elegido por su rango', () => {
    const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, ...rangoDelPeriodo('mes', HOY) };

    expect(periodoActivo(filtros, HOY)).toBe('mes');
  });

  test('un rango a mano, o sin rango activo, no marca ningún período', () => {
    expect(periodoActivo({ ...filtrosAgendaIniciales(HOY), conRango: true }, HOY)).toBe('');
    expect(periodoActivo({ ...filtrosAgendaIniciales(HOY), conRango: true, fecha_desde: '2026-10-15' }, HOY)).toBe('');
    expect(periodoActivo({ ...filtrosAgendaIniciales(HOY), ...rangoDelPeriodo('mes', HOY) }, HOY)).toBe('');
  });

  test('cambia solo al día siguiente: el período es relativo a hoy', () => {
    const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, ...rangoDelPeriodo('semana', HOY) };

    expect(periodoActivo(filtros, '2026-11-13')).toBe('');
  });
});

describe('fechaInicialDeAlta', () => {
  test('sin rango usa el día que se está viendo', () => {
    expect(fechaInicialDeAlta({ ...filtrosAgendaIniciales(HOY), fecha: '2026-11-20' }, HOY)).toBe('2026-11-20');
  });

  test('sin día válido usa hoy', () => {
    expect(fechaInicialDeAlta({ ...filtrosAgendaIniciales(HOY), fecha: '' }, HOY)).toBe(HOY);
  });

  test('con rango usa su inicio si es hoy o futuro', () => {
    const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, fecha_desde: '2026-11-20', fecha_hasta: '2026-11-25' };

    expect(fechaInicialDeAlta(filtros, HOY)).toBe('2026-11-20');
  });

  test('con un rango que empieza en el pasado (por ejemplo, el último mes) usa hoy: no se puede reservar atrás', () => {
    const filtros = { ...filtrosAgendaIniciales(HOY), conRango: true, ...rangoDelPeriodo('mes', HOY) };

    expect(fechaInicialDeAlta(filtros, HOY)).toBe(HOY);
  });

  test('con el inicio del rango vacío usa hoy', () => {
    expect(fechaInicialDeAlta({ ...filtrosAgendaIniciales(HOY), conRango: true, fecha_desde: '' }, HOY)).toBe(HOY);
  });
});

describe('vistaDeAgenda', () => {
  test('reconoce los turnos fijos y cae a las reservas ante un valor desconocido', () => {
    expect(vistaDeAgenda('turnos-fijos')).toBe('turnos-fijos');
    expect(vistaDeAgenda('reservas')).toBe('reservas');
    expect(vistaDeAgenda('otra')).toBe('reservas');
    expect(vistaDeAgenda(null)).toBe('reservas');
  });
});

describe('estadosSiguientes', () => {
  test('antes del turno no ofrece ausente ni completada', () => {
    expect(estadosSiguientes(reserva(1), AHORA)).toEqual([2, 3]);
    expect(estadosSiguientes(reserva(2), AHORA)).toEqual([3]);
    expect(estadosSiguientes(reserva(3), AHORA)).toEqual([]);
  });

  test('una vez iniciado el turno ofrece ausente y completada, y se corrigen entre sí', () => {
    const iniciada = (estado) => reserva(estado, '2026-11-12', '14:00:00');

    expect(estadosSiguientes(iniciada(1), AHORA)).toEqual([2, 3, 6, 7]);
    expect(estadosSiguientes(iniciada(3), AHORA)).toEqual([6, 7]);
    expect(estadosSiguientes(iniciada(6), AHORA)).toEqual([7]);
    expect(estadosSiguientes(iniciada(7), AHORA)).toEqual([6]);
  });

  test('una reserva cancelada no cambia de estado por esta vía', () => {
    expect(estadosSiguientes(reserva(4), AHORA)).toEqual([]);
    expect(estadosSiguientes(reserva(5), AHORA)).toEqual([]);
  });

  test('sin seña acordada no se ofrece «Señada»: se confirma o se cobra el total', () => {
    const sinSena = (estado, hora = '20:00:00') => reserva(estado, '2026-11-12', hora, '0.00');

    expect(estadosSiguientes(sinSena(1), AHORA)).toEqual([2]);
    expect(estadosSiguientes(sinSena(2), AHORA)).toEqual([]);
    expect(estadosSiguientes(sinSena(1, '14:00:00'), AHORA)).toEqual([2, 6, 7]);
  });

  test('una señada antigua sin montos conserva sus salidas (ausente y completada)', () => {
    expect(estadosSiguientes(reserva(3, '2026-11-12', '14:00:00', '0.00'), AHORA)).toEqual([6, 7]);
  });
});

describe('estadosDeReapertura', () => {
  test('con seña ofrece pendiente, confirmada y señada', () => {
    expect(estadosDeReapertura(reserva(4))).toEqual([1, 2, 3]);
  });

  test('sin seña no ofrece señada', () => {
    expect(estadosDeReapertura(reserva(5, '2026-11-12', '20:00:00', '0.00'))).toEqual([1, 2]);
  });
});

describe('puedeCancelarElComplejo', () => {
  test('solo las reservas pendientes, confirmadas o señadas', () => {
    expect([1, 2, 3].every((estado) => puedeCancelarElComplejo(reserva(estado)))).toBe(true);
    expect([4, 5, 6, 7].some((estado) => puedeCancelarElComplejo(reserva(estado)))).toBe(false);
  });
});

describe('puedeReabrir', () => {
  test('una cancelada con el turno por jugar se puede reabrir', () => {
    expect(puedeReabrir(reserva(4, '2026-11-20'), AHORA)).toBe(true);
    expect(puedeReabrir(reserva(5, '2026-11-12', '20:00:00'), AHORA)).toBe(true);
  });

  test('si el turno ya empezó, o no está cancelada, no se ofrece', () => {
    expect(puedeReabrir(reserva(5, '2026-11-12', '14:00:00'), AHORA)).toBe(false);
    expect(puedeReabrir(reserva(2, '2026-11-20'), AHORA)).toBe(false);
  });
});

describe('validarReservaManual', () => {
  const valido = {
    ...VALORES_RESERVA_MANUAL_INICIALES,
    cancha: '3',
    fecha_turno: '2026-11-20',
    hora_inicio: '20:00',
    nombre_cliente_manual: 'Cliente de muestra',
  };

  test('una reserva completa no tiene errores', () => {
    expect(validarReservaManual(valido, HOY)).toEqual({});
  });

  test('exige cancha, fecha, hora y nombre', () => {
    expect(Object.keys(validarReservaManual(VALORES_RESERVA_MANUAL_INICIALES, HOY)).sort()).toEqual([
      'cancha', 'fecha_turno', 'hora_inicio', 'nombre_cliente_manual',
    ]);
  });

  test('rechaza una fecha pasada y un nombre solo con espacios', () => {
    const errores = validarReservaManual({ ...valido, fecha_turno: '2026-11-11', nombre_cliente_manual: '   ' }, HOY);

    expect(Object.keys(errores).sort()).toEqual(['fecha_turno', 'nombre_cliente_manual']);
  });
});

describe('cuerpoReservaManual', () => {
  test('arma el cuerpo con la cancha numérica y los textos recortados', () => {
    const cuerpo = cuerpoReservaManual({
      cancha: '3',
      fecha_turno: '2026-11-20',
      hora_inicio: '20:00',
      nombre_cliente_manual: ' Cliente de muestra ',
      telefono_cliente_manual: ' 3777 001234 ',
      observaciones: ' Trae pelota ',
    });

    expect(cuerpo).toEqual({
      cancha: 3,
      fecha_turno: '2026-11-20',
      hora_inicio: '20:00',
      nombre_cliente_manual: 'Cliente de muestra',
      telefono_cliente_manual: '3777 001234',
      observaciones: 'Trae pelota',
    });
  });
});

describe('observaciones de una reserva', () => {
  test('un texto de hasta 255 caracteres es válido, también vacío', () => {
    expect(errorDeObservaciones('')).toBeUndefined();
    expect(errorDeObservaciones('x'.repeat(255))).toBeUndefined();
    expect(errorDeObservaciones(null)).toBeUndefined();
  });

  test('más de 255 caracteres informa el máximo', () => {
    expect(errorDeObservaciones('x'.repeat(256))).toBe('Las observaciones no pueden superar los 255 caracteres.');
  });

  test('los espacios de los extremos no cuentan para el largo', () => {
    expect(errorDeObservaciones(`  ${'x'.repeat(255)}  `)).toBeUndefined();
  });

  test('detecta si el texto difiere del guardado sin contar espacios en los extremos', () => {
    expect(observacionesModificadas({ observaciones: 'Trae pelota' }, 'Trae pelota ')).toBe(false);
    expect(observacionesModificadas({ observaciones: 'Trae pelota' }, 'Trae red')).toBe(true);
    expect(observacionesModificadas({ observaciones: '' }, '')).toBe(false);
    expect(observacionesModificadas({}, 'Nueva nota')).toBe(true);
    expect(observacionesModificadas({ observaciones: 'Nota' }, '')).toBe(true);
  });
});
