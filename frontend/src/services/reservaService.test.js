import { beforeEach, describe, expect, test, vi } from 'vitest';

const apiDjango = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('./api.js', () => ({ apiDjango }));

const {
  actualizarReservaAgenda,
  anularCobroReserva,
  confirmarSenaReserva,
  crearReserva,
  informarTransferencia,
  rechazarTransferencia,
  registrarPagoReserva,
} = await import('./reservaService.js');

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

describe('aviso de transferencia', () => {
  test('informa quién transfirió y el número de operación de una reserva propia', async () => {
    apiDjango.post.mockResolvedValue({ data: { id: 3, transferencia_informada: true } });

    await expect(informarTransferencia(3, { titular: 'Marta López', referencia: 'OP-48213' })).resolves.toEqual({
      id: 3,
      transferencia_informada: true,
    });
    expect(apiDjango.post).toHaveBeenCalledWith('/api/reservas/3/informar-transferencia/', {
      titular: 'Marta López',
      referencia: 'OP-48213',
    });
  });

  test('solo envía los dos campos aunque reciba de más y codifica el id', async () => {
    apiDjango.post.mockResolvedValue({ data: {} });

    await informarTransferencia('3/../x', { titular: 'Ana', referencia: 'ABC', otro: 'no' });

    expect(apiDjango.post).toHaveBeenCalledWith('/api/reservas/3%2F..%2Fx/informar-transferencia/', {
      titular: 'Ana',
      referencia: 'ABC',
    });
  });

  test('un rechazo del servidor llega tal cual a quien llama', async () => {
    const rechazo = Object.assign(new Error('La seña de esta reserva ya está registrada.'), { status: 400 });
    apiDjango.post.mockRejectedValue(rechazo);

    await expect(informarTransferencia(3, { titular: 'Ana', referencia: 'ABC' })).rejects.toBe(rechazo);
  });
});

describe('correcciones del personal', () => {
  test('rechaza la transferencia con un motivo y una nota', async () => {
    apiDjango.post.mockResolvedValue({ data: { id: 7, transferencia_rechazada: true } });

    await expect(rechazarTransferencia(7, { motivo: 1, nota: 'No llegó' })).resolves.toEqual({ id: 7, transferencia_rechazada: true });
    expect(apiDjango.post).toHaveBeenCalledWith('/api/agenda/7/rechazar-transferencia/', { motivo: 1, nota: 'No llegó' });
  });

  test('anula el cobro de una reserva', async () => {
    apiDjango.post.mockResolvedValue({ data: { id: 7, monto_pagado: '0.00' } });

    await expect(anularCobroReserva(7)).resolves.toEqual({ id: 7, monto_pagado: '0.00' });
    expect(apiDjango.post).toHaveBeenCalledWith('/api/agenda/7/anular-cobro/');
  });

  test('codifica el id en la ruta y reenvía los rechazos del servidor', async () => {
    const rechazo = Object.assign(new Error('Esta reserva no tiene un cobro registrado.'), { status: 400 });
    apiDjango.post.mockRejectedValue(rechazo);

    await expect(anularCobroReserva('7/../x')).rejects.toBe(rechazo);
    expect(apiDjango.post).toHaveBeenCalledWith('/api/agenda/7%2F..%2Fx/anular-cobro/');
  });
});
