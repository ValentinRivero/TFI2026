import { describe, expect, test } from 'vitest';
import { conConfirmacion, leerConflictos } from './conflictos.js';

const error409 = (extra) => ({ status: 409, mensaje: 'El cambio deja fuera de la grilla 1 reserva(s).', extra });

describe('leerConflictos', () => {
  test('un 409 que pide confirmación devuelve el detalle normalizado', () => {
    const conflictos = leerConflictos(error409({
      requiere_confirmacion: true,
      conflictos: {
        cantidad: 2,
        reservas: [{ id: 41, fecha_turno: '2026-11-24', hora_inicio: '20:00', estado: 3, motivo: 'Fuera de turno' }],
        turnos_fijos: [{ id: 7, dia_semana: 2, hora_inicio: '21:00', motivo: 'Fuera de turno' }],
      },
    }));

    expect(conflictos.cantidad).toBe(2);
    expect(conflictos.reservas).toHaveLength(1);
    expect(conflictos.turnosFijos).toHaveLength(1);
    expect(conflictos.mensaje).toContain('1 reserva');
  });

  test('sin cantidad informada la calcula con las listas', () => {
    const conflictos = leerConflictos(error409({
      requiere_confirmacion: true,
      conflictos: { reservas: [{ id: 1 }], turnos_fijos: [{ id: 2 }, { id: 3 }] },
    }));

    expect(conflictos.cantidad).toBe(3);
  });

  test('un 409 sin confirmación posible no se considera conflicto confirmable', () => {
    expect(leerConflictos(error409({}))).toBeNull();
  });

  test('otros códigos o errores ausentes devuelven null', () => {
    expect(leerConflictos({ status: 400, extra: { requiere_confirmacion: true } })).toBeNull();
    expect(leerConflictos(null)).toBeNull();
  });

  test('listas con otro formato se tratan como vacías', () => {
    const conflictos = leerConflictos(error409({ requiere_confirmacion: true, conflictos: { reservas: 'x' } }));

    expect(conflictos.reservas).toEqual([]);
    expect(conflictos.cantidad).toBe(0);
  });
});

describe('conConfirmacion', () => {
  test('agrega confirmar sin alterar el original', () => {
    const original = { duracion_turno_min: 90 };

    expect(conConfirmacion(original)).toEqual({ duracion_turno_min: 90, confirmar: true });
    expect(original).toEqual({ duracion_turno_min: 90 });
  });
});
