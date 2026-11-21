import { beforeEach, describe, expect, test, vi } from 'vitest';

const apiDjango = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('./api.js', () => ({ apiDjango }));

const { actualizarReservaAgenda, confirmarSenaReserva, crearReserva, registrarPagoReserva } = await import('./reservaService.js');

beforeEach(() => {
  Object.values(apiDjango).forEach((funcion) => funcion.mockReset());
});

describe('cobro de reservas', () => {
  test('confirma la seña de una reserva de la agenda', async () => {
    apiDjango.post.mockResolvedValue({ data: { id: 7, estado: 3, monto_pagado: '11400.00' } });

    await expect(confirmarSenaReserva(7)).resolves.toEqual({ id: 7, estado: 3, monto_pagado: '11400.00' });
    expect(apiDjango.post).toHaveBeenCalledWith('/api/agenda/7/confirmar-sena/');
  });

  test('registra el pago total de una reserva de la agenda', async () => {
    apiDjango.post.mockResolvedValue({ data: { id: 7, estado_pago: 4 } });

    await expect(registrarPagoReserva(7)).resolves.toEqual({ id: 7, estado_pago: 4 });
    expect(apiDjango.post).toHaveBeenCalledWith('/api/agenda/7/registrar-pago/');
  });

  test('codifica el id en la ruta', async () => {
    apiDjango.post.mockResolvedValue({ data: {} });

    await confirmarSenaReserva('7/../x');

    expect(apiDjango.post).toHaveBeenCalledWith('/api/agenda/7%2F..%2Fx/confirmar-sena/');
  });

  test('un rechazo del servidor llega tal cual a quien llama', async () => {
    const rechazo = Object.assign(new Error('La reserva ya está saldada.'), { status: 400 });
    apiDjango.post.mockRejectedValue(rechazo);

    await expect(registrarPagoReserva(7)).rejects.toBe(rechazo);
  });
});

describe('alta de reserva', () => {
  test('devuelve la reserva con sus montos y los datos de transferencia', async () => {
    const reserva = { id: 3, monto_sena: '11400.00', datos_transferencia: { alias: 'YACARE.SENA', titular: '' } };
    apiDjango.post.mockResolvedValue({ data: reserva });

    await expect(crearReserva({ canchaId: 2, fechaTurno: '2026-11-17', horaInicio: '14:00:00' })).resolves.toEqual(reserva);
    expect(apiDjango.post).toHaveBeenCalledWith('/api/reservas/', { cancha: 2, fecha_turno: '2026-11-17', hora_inicio: '14:00' });
  });
});

describe('observaciones de la agenda', () => {
  test('edita solo las observaciones de la reserva', async () => {
    apiDjango.patch.mockResolvedValue({ data: { id: 7, observaciones: 'Trae pelota' } });

    await expect(actualizarReservaAgenda(7, { observaciones: 'Trae pelota' })).resolves.toEqual({ id: 7, observaciones: 'Trae pelota' });
    expect(apiDjango.patch).toHaveBeenCalledWith('/api/agenda/7/', { observaciones: 'Trae pelota' });
  });
});
