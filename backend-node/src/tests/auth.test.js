import { jest } from '@jest/globals';
import { randomUUID } from 'node:crypto';

import express from 'express';
import jwt from 'jsonwebtoken';
import request from 'supertest';

import { manejarErrores } from '../middlewares/errores.middleware.js';
import { autenticar } from '../middlewares/auth.middleware.js';

const CLAVE = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
const SIN_SESION = { error: true, mensaje: 'Debés iniciar sesión para acceder a este recurso.' };
const TOKEN_INVALIDO = { error: true, mensaje: 'El token es inválido o expiró.' };

const app = express();
app.get('/privado', autenticar, (req, res) => res.json({ usuario: req.usuario }));
app.use(manejarErrores);

// Mismos datos y firma que el access token de Django (SimpleJWT con `TokenConRolSerializer`).
const tokenDeDjango = ({ clave = CLAVE, algoritmo = 'HS256', vence = '30m', ...datos } = {}) => jwt.sign(
  { token_type: 'access', jti: randomUUID(), usuario_id: '7', rol: 'JUGADOR', ...datos },
  clave,
  { algorithm: algoritmo, expiresIn: vence },
);

const pedir = (encabezado) => {
  const pedido = request(app).get('/privado');
  return encabezado === undefined ? pedido : pedido.set('Authorization', encabezado);
};

beforeEach(() => {
  process.env.JWT_SIGNING_KEY = CLAVE;
});

describe('Autenticación con el JWT de Django', () => {
  test('el id llega como número aunque SimpleJWT lo firme como texto', async () => {
    const respuesta = await pedir(`Bearer ${tokenDeDjango({ usuario_id: '42' })}`);

    expect(respuesta.body.usuario.id).toBe(42);
  });

  test('un access token válido identifica al usuario y su rol', async () => {
    const respuesta = await pedir(`Bearer ${tokenDeDjango()}`);

    expect(respuesta.status).toBe(200);
    expect(respuesta.body).toEqual({ usuario: { id: 7, rol: 'JUGADOR' } });
  });

  test('sin encabezado Authorization responde 401 con el mensaje de Django', async () => {
    const respuesta = await pedir();

    expect(respuesta.status).toBe(401);
    expect(respuesta.body).toEqual(SIN_SESION);
    expect(respuesta.headers['www-authenticate']).toBe('Bearer realm="api"');
  });

  test.each([
    ['otro esquema', (token) => `Token ${token}`],
    ['esquema en minúsculas', (token) => `bearer ${token}`],
  ])('con %s se trata como sin sesión, igual que Django', async (_caso, armar) => {
    const respuesta = await pedir(armar(tokenDeDjango()));

    expect(respuesta.status).toBe(401);
    expect(respuesta.body).toEqual(SIN_SESION);
  });

  test.each([
    ['Bearer sin token', () => 'Bearer'],
    ['Bearer con espacios de más', (token) => `Bearer ${token} extra`],
    ['texto que no es un JWT', () => 'Bearer no-es-un-jwt'],
  ])('%s responde 401 por token inválido', async (_caso, armar) => {
    const respuesta = await pedir(armar(tokenDeDjango()));

    expect(respuesta.status).toBe(401);
    expect(respuesta.body).toEqual(TOKEN_INVALIDO);
  });

  test('un token vencido responde 401', async () => {
    const respuesta = await pedir(`Bearer ${tokenDeDjango({ vence: -10 })}`);

    expect(respuesta.status).toBe(401);
    expect(respuesta.body).toEqual(TOKEN_INVALIDO);
  });

  test('un token firmado con otra clave responde 401', async () => {
    const respuesta = await pedir(`Bearer ${tokenDeDjango({ clave: 'otra-clave-de-un-atacante-con-largo-suficiente-000' })}`);

    expect(respuesta.status).toBe(401);
  });

  test('un token con los datos alterados después de firmarlo responde 401', async () => {
    const [cabecera, , firma] = tokenDeDjango().split('.');
    const datos = Buffer.from(JSON.stringify({
      token_type: 'access', usuario_id: 7, rol: 'SUPERADMIN', exp: Math.floor(Date.now() / 1000) + 600,
    })).toString('base64url');

    expect((await pedir(`Bearer ${cabecera}.${datos}.${firma}`)).status).toBe(401);
  });

  test('un token sin firma (algoritmo "none") responde 401', async () => {
    const sinFirma = jwt.sign({ token_type: 'access', usuario_id: 7, rol: 'SUPERADMIN' }, '', { algorithm: 'none' });

    expect((await pedir(`Bearer ${sinFirma}`)).status).toBe(401);
  });

  test('solo acepta HS256 aunque la firma con otro algoritmo use la misma clave', async () => {
    expect((await pedir(`Bearer ${tokenDeDjango({ algoritmo: 'HS512' })}`)).status).toBe(401);
  });

  test('un refresh token no sirve como access aunque tenga firma válida', async () => {
    const respuesta = await pedir(`Bearer ${tokenDeDjango({ token_type: 'refresh', vence: '1d' })}`);

    expect(respuesta.status).toBe(401);
    expect(respuesta.body).toEqual(TOKEN_INVALIDO);
  });

  test.each([
    ['sin usuario_id', { usuario_id: undefined }],
    ['con usuario_id no numérico', { usuario_id: 'admin' }],
    ['con usuario_id con texto agregado', { usuario_id: '7 OR 1=1' }],
    ['con usuario_id cero', { usuario_id: '0' }],
    ['con usuario_id negativo', { usuario_id: '-7' }],
    ['con usuario_id decimal', { usuario_id: '7.5' }],
    ['sin rol', { rol: undefined }],
    ['con rol vacío', { rol: '' }],
  ])('un token %s responde 401', async (_caso, datos) => {
    expect((await pedir(`Bearer ${tokenDeDjango(datos)}`)).status).toBe(401);
  });

  test('sin clave configurada responde 500 genérico en lugar de aceptar o rechazar a ciegas', async () => {
    const token = tokenDeDjango();
    delete process.env.JWT_SIGNING_KEY;
    const consola = jest.spyOn(console, 'error').mockImplementation(() => {});

    const respuesta = await pedir(`Bearer ${token}`);

    expect(respuesta.status).toBe(500);
    expect(respuesta.body).toEqual({ error: true, mensaje: 'Error interno del servidor.' });
    consola.mockRestore();
  });
});
