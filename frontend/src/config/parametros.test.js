import { describe, expect, it } from 'vitest';

import { resolverUrlWs } from './parametros.js';
import { armarUrlDisponibilidad } from '../utils/tiempoReal.js';

describe('resolverUrlWs', () => {
  it('sin variable usa el backend local de desarrollo', () => {
    expect(resolverUrlWs(undefined)).toBe('ws://localhost:8000');
  });

  it('respeta una dirección explícita', () => {
    expect(resolverUrlWs('wss://otro.talibre.test')).toBe('wss://otro.talibre.test');
  });

  it('vacía, toma el mismo origen con wss si la página se abrió por HTTPS', () => {
    expect(resolverUrlWs('', { protocol: 'https:', host: 'talibre.test' })).toBe('wss://talibre.test');
  });

  it('vacía, usa ws si la página se abrió por HTTP', () => {
    expect(resolverUrlWs('', { protocol: 'http:', host: 'localhost:8080' })).toBe('ws://localhost:8080');
  });

  it('el canal de un complejo queda como wss://<dominio>/ws/... sin duplicar barras', () => {
    const base = resolverUrlWs('', { protocol: 'https:', host: 'talibre.test' });
    expect(armarUrlDisponibilidad(base, 7, 'token')).toBe('wss://talibre.test/ws/complejos/7/disponibilidad/?token=token');
  });
});
