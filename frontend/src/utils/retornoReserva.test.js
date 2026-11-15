import { describe, expect, test } from 'vitest';
import { aParametrosRetorno, leerRetorno, rutaDeRetorno } from './retornoReserva.js';

describe('aParametrosRetorno y leerRetorno', () => {
  test('el turno que se guarda es el que se retoma', () => {
    const consulta = aParametrosRetorno({ fecha: '2026-11-24', canchaId: 3, horaInicio: '20:00:00' });

    expect(leerRetorno(new URLSearchParams(consulta))).toEqual({
      fecha: '2026-11-24',
      canchaId: 3,
      horaInicio: '20:00',
      reservar: true,
    });
  });

  test('sin el aviso de reservar solo se restaura la elección', () => {
    const retorno = leerRetorno(new URLSearchParams('fecha=2026-11-24&cancha=3&hora=20:00'));

    expect(retorno.reservar).toBe(false);
  });

  test.each([
    ['sin parámetros', ''],
    ['fecha inexistente', 'fecha=2026-02-30&cancha=3&hora=20:00'],
    ['fecha con otro formato', 'fecha=24/11/2026&cancha=3&hora=20:00'],
    ['cancha no numérica', 'fecha=2026-11-24&cancha=abc&hora=20:00'],
    ['cancha cero', 'fecha=2026-11-24&cancha=0&hora=20:00'],
    ['hora inválida', 'fecha=2026-11-24&cancha=3&hora=tarde'],
    ['falta la hora', 'fecha=2026-11-24&cancha=3'],
  ])('descarta un retorno incompleto o manipulado: %s', (_caso, consulta) => {
    expect(leerRetorno(new URLSearchParams(consulta))).toBeNull();
  });
});

describe('rutaDeRetorno', () => {
  test('conserva la query string de la ruta de origen', () => {
    expect(rutaDeRetorno({ pathname: '/complejos/5', search: '?fecha=2026-11-24' })).toBe('/complejos/5?fecha=2026-11-24');
  });

  test('una ruta sin query string queda igual', () => {
    expect(rutaDeRetorno({ pathname: '/mis-reservas' })).toBe('/mis-reservas');
  });

  test('sin ruta de origen devuelve null', () => {
    expect(rutaDeRetorno(undefined)).toBeNull();
    expect(rutaDeRetorno({})).toBeNull();
  });
});
