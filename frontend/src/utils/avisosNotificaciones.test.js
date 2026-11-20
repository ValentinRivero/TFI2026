import { describe, expect, test, vi } from 'vitest';
import {
  alMarcarLeida,
  alMarcarTodasLeidas,
  anunciarLeida,
  anunciarTodasLeidas,
} from './avisosNotificaciones.js';

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

  test('el aviso de "todas leídas" llega solo a sus suscriptores, no a los de una lectura', () => {
    const deTodas = vi.fn();
    const deUna = vi.fn();
    const cancelarTodas = alMarcarTodasLeidas(deTodas);
    const cancelarUna = alMarcarLeida(deUna);

    anunciarTodasLeidas();
    expect(deTodas).toHaveBeenCalledTimes(1);
    expect(deUna).not.toHaveBeenCalled();

    anunciarLeida();
    expect(deTodas).toHaveBeenCalledTimes(1);
    expect(deUna).toHaveBeenCalledTimes(1);

    cancelarTodas();
    cancelarUna();
  });

  test('una suscripción a "todas leídas" cancelada deja de recibir avisos', () => {
    const escuchar = vi.fn();
    alMarcarTodasLeidas(escuchar)();

    anunciarTodasLeidas();
    expect(escuchar).not.toHaveBeenCalled();
  });

  test('una suscripción cancelada deja de recibir avisos', () => {
    const escuchar = vi.fn();
    const cancelar = alMarcarLeida(escuchar);
    cancelar();

    anunciarLeida();
    expect(escuchar).not.toHaveBeenCalled();
  });
});
