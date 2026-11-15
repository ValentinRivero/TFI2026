import { describe, expect, test, vi } from 'vitest';
import { alMarcarLeida, anunciarLeida } from './avisosNotificaciones.js';

describe('avisosNotificaciones', () => {
  test('avisa a cada suscriptor cuando se anuncia una lectura', () => {
    const primero = vi.fn();
    const segundo = vi.fn();
    const cancelarPrimero = alMarcarLeida(primero);
    const cancelarSegundo = alMarcarLeida(segundo);

    anunciarLeida();
    expect(primero).toHaveBeenCalledTimes(1);
    expect(segundo).toHaveBeenCalledTimes(1);

    cancelarPrimero();
    cancelarSegundo();
  });

  test('una suscripción cancelada deja de recibir avisos', () => {
    const escuchar = vi.fn();
    const cancelar = alMarcarLeida(escuchar);
    cancelar();

    anunciarLeida();
    expect(escuchar).not.toHaveBeenCalled();
  });
});
