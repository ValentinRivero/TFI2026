import { describe, expect, test } from 'vitest';
import { datosDeAccess, decodificarJwt } from './jwt.js';

const codificar = (objeto) => Buffer.from(JSON.stringify(objeto), 'utf8').toString('base64url');
const jwt = (payload) => `${codificar({ alg: 'HS256', typ: 'JWT' })}.${codificar(payload)}.firma`;

describe('decodificarJwt', () => {
  test('lee el payload', () => {
    expect(decodificarJwt(jwt({ rol: 'JUGADOR', usuario_id: '7' }))).toEqual({ rol: 'JUGADOR', usuario_id: '7' });
  });

  test('respeta los caracteres con tilde y la codificación base64url', () => {
    const payload = { rol: 'DUENO_COMPLEJO', nombre: 'Ñandubay ¿qué?', relleno: '>>>???~~~' };

    expect(decodificarJwt(jwt(payload))).toEqual(payload);
  });

  test.each([
    ['no es texto', 123],
    ['es nulo', null],
    ['está vacío', ''],
    ['tiene menos de tres partes', 'a.b'],
    ['tiene más de tres partes', 'a.b.c.d'],
    ['tiene el payload vacío', 'a..c'],
    ['tiene un payload que no es base64', 'a.@@@.c'],
    ['tiene un payload que no es JSON', `a.${Buffer.from('hola').toString('base64url')}.c`],
    ['tiene un payload que no es un objeto', `a.${codificar([1, 2])}.c`],
    ['tiene un payload nulo', `a.${codificar(null)}.c`],
  ])('devuelve null si el token %s', (_motivo, token) => {
    expect(decodificarJwt(token)).toBeNull();
  });
});

describe('datosDeAccess', () => {
  test('convierte usuario_id de texto a número y lee rol y vencimiento', () => {
    expect(datosDeAccess(jwt({ usuario_id: '12', rol: 'SUPERADMIN', exp: 1790000000 }))).toEqual({
      usuarioId: 12, rol: 'SUPERADMIN', expira: 1790000000,
    });
  });

  test('un rol desactivado llega como nulo', () => {
    expect(datosDeAccess(jwt({ usuario_id: '3', rol: null })).rol).toBeNull();
    expect(datosDeAccess(jwt({ usuario_id: '3', rol: '' })).rol).toBeNull();
  });

  test.each(['abc', '0', '-4', '1.5', null, undefined])('un usuario_id inválido (%s) da null', (valor) => {
    expect(datosDeAccess(jwt({ usuario_id: valor, rol: 'JUGADOR' })).usuarioId).toBeNull();
  });

  test('sin vencimiento numérico, expira es null', () => {
    expect(datosDeAccess(jwt({ usuario_id: '1', exp: 'pronto' })).expira).toBeNull();
  });

  test('un token inválido da null', () => {
    expect(datosDeAccess('no-es-un-token')).toBeNull();
  });
});
