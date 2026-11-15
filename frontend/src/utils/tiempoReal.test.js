import { describe, expect, test } from 'vitest';
import { armarUrlDisponibilidad, calcularEspera, eventoAfectaGrilla } from './tiempoReal.js';

const PARAMS = { reconexionInicialMs: 1000, reconexionMaximaMs: 30000, jitter: 0.3 };
const SIN_JITTER = () => 0.5;

describe('calcularEspera', () => {
  test('duplica la espera en cada intento', () => {
    expect([0, 1, 2, 3].map((n) => calcularEspera(n, PARAMS, SIN_JITTER))).toEqual([1000, 2000, 4000, 8000]);
  });

  test('no pasa del máximo', () => {
    expect(calcularEspera(10, PARAMS, SIN_JITTER)).toBe(30000);
    expect(calcularEspera(1000, PARAMS, SIN_JITTER)).toBe(30000);
  });

  test('el jitter varía hasta el porcentaje configurado en ambos sentidos', () => {
    expect(calcularEspera(1, PARAMS, () => 0)).toBe(1400);
    expect(calcularEspera(1, PARAMS, () => 0.999999)).toBe(2600);
  });

  test('un intento negativo se trata como el primero', () => {
    expect(calcularEspera(-3, PARAMS, SIN_JITTER)).toBe(1000);
  });

  test('con los parámetros por defecto queda dentro del rango esperado', () => {
    const espera = calcularEspera(0);

    expect(espera).toBeGreaterThanOrEqual(700);
    expect(espera).toBeLessThanOrEqual(1300);
  });
});

describe('armarUrlDisponibilidad', () => {
  test('sin sesión no lleva token', () => {
    expect(armarUrlDisponibilidad('ws://localhost:8000', 12)).toBe('ws://localhost:8000/ws/complejos/12/disponibilidad/');
  });

  test('con sesión envía el token codificado', () => {
    expect(armarUrlDisponibilidad('wss://talibre.test/', 3, 'a.b+c/d=')).toBe(
      'wss://talibre.test/ws/complejos/3/disponibilidad/?token=a.b%2Bc%2Fd%3D',
    );
  });
});

describe('eventoAfectaGrilla', () => {
  const evento = (cambios) => ({
    event: 'grilla_actualizada',
    cancha_id: 5,
    fecha_desde: '2026-11-20',
    fecha_hasta: '2026-11-20',
    hora_inicio: '20:00:00',
    hora_fin: '21:00:00',
    ...cambios,
  });

  test('ignora otros tipos de mensaje o formas inesperadas', () => {
    expect(eventoAfectaGrilla({ event: 'otro' }, { fecha: '2026-11-20' })).toBe(false);
    expect(eventoAfectaGrilla(null, { fecha: '2026-11-20' })).toBe(false);
    expect(eventoAfectaGrilla('texto', { fecha: '2026-11-20' })).toBe(false);
  });

  test('afecta la fecha visible dentro del rango', () => {
    expect(eventoAfectaGrilla(evento(), { fecha: '2026-11-20', canchaIds: [5, 6] })).toBe(true);
  });

  test('no afecta otra fecha', () => {
    expect(eventoAfectaGrilla(evento(), { fecha: '2026-11-21', canchaIds: [5] })).toBe(false);
    expect(eventoAfectaGrilla(evento(), { fecha: '2026-11-19', canchaIds: [5] })).toBe(false);
  });

  test('un rango cubre sus extremos', () => {
    const rango = evento({ fecha_desde: '2026-11-20', fecha_hasta: '2026-11-25' });

    expect(eventoAfectaGrilla(rango, { fecha: '2026-11-20' })).toBe(true);
    expect(eventoAfectaGrilla(rango, { fecha: '2026-11-25' })).toBe(true);
    expect(eventoAfectaGrilla(rango, { fecha: '2026-11-26' })).toBe(false);
  });

  test('una vigencia sin fin afecta toda fecha posterior al inicio', () => {
    const sinFin = evento({ fecha_hasta: null });

    expect(eventoAfectaGrilla(sinFin, { fecha: '2027-03-01' })).toBe(true);
    expect(eventoAfectaGrilla(sinFin, { fecha: '2026-11-19' })).toBe(false);
  });

  test('un evento global afecta a todas las canchas', () => {
    expect(eventoAfectaGrilla(evento({ cancha_id: null }), { fecha: '2026-11-20', canchaIds: [1] })).toBe(true);
  });

  test('un evento de una cancha que la grilla no muestra se ignora', () => {
    expect(eventoAfectaGrilla(evento({ cancha_id: 99 }), { fecha: '2026-11-20', canchaIds: [5, 6] })).toBe(false);
  });

  test('sin canchas conocidas todavía se considera relevante', () => {
    expect(eventoAfectaGrilla(evento({ cancha_id: 99 }), { fecha: '2026-11-20', canchaIds: null })).toBe(true);
  });

  test('sin rango de fechas se considera relevante', () => {
    const sinFechas = { event: 'grilla_actualizada', cancha_id: null };

    expect(eventoAfectaGrilla(sinFechas, { fecha: '2026-11-20' })).toBe(true);
  });
});
