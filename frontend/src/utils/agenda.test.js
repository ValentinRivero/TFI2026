import { describe, expect, test } from 'vitest';
import {
  aParametrosAgenda,
  cuerpoReservaManual,
  estadosSiguientes,
  filtrosAgendaIniciales,
  puedeCancelarElComplejo,
  puedeReabrir,
  validarReservaManual,
  VALORES_RESERVA_MANUAL_INICIALES,
  vistaDeAgenda,
} from './agenda.js';

const HOY = '2026-11-12';
const reserva = (estado, fecha = '2026-11-12', hora = '20:00:00') => ({ estado, fecha_turno: fecha, hora_inicio: hora });
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
