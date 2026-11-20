import { beforeEach, describe, expect, test, vi } from 'vitest';

const apiNode = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn() }));
vi.mock('./api.js', () => ({ apiNode }));

const { marcarNotificacionLeida, marcarTodasMisNotificacionesLeidas } = await import('./notificacionService.js');

beforeEach(() => {
  apiNode.get.mockReset();
  apiNode.patch.mockReset();
});

describe('marcarTodasMisNotificacionesLeidas', () => {
  test('hace una sola petición PATCH a la ruta propia, sin identificar a la cuenta', async () => {
    apiNode.patch.mockResolvedValue({ data: { actualizadas: 4 } });

    await expect(marcarTodasMisNotificacionesLeidas()).resolves.toBe(4);
    expect(apiNode.patch).toHaveBeenCalledTimes(1);
    expect(apiNode.patch).toHaveBeenCalledWith('/api/actividad/notificaciones/mias/leidas');
  });

  test('una respuesta sin cantidad se toma como cero', async () => {
    apiNode.patch.mockResolvedValue({ data: {} });

    await expect(marcarTodasMisNotificacionesLeidas()).resolves.toBe(0);
  });

  test('un error del servicio se propaga para que la pantalla lo muestre', async () => {
    apiNode.patch.mockRejectedValue(new Error('502'));

    await expect(marcarTodasMisNotificacionesLeidas()).rejects.toThrow('502');
  });
});

describe('marcarNotificacionLeida', () => {
  test('sigue marcando una sola notificación por su id', async () => {
    apiNode.patch.mockResolvedValue({ data: { _id: 'abc', estado: 2 } });

    const notificacion = await marcarNotificacionLeida('abc');

    expect(apiNode.patch).toHaveBeenCalledWith('/api/actividad/notificaciones/abc', { estado: 2 });
    expect(notificacion.id).toBe('abc');
  });
});
