import { randomUUID } from 'node:crypto';

import { jest } from '@jest/globals';
import express from 'express';
import jwt from 'jsonwebtoken';
import request from 'supertest';

import { autenticar } from '../middlewares/auth.middleware.js';
import { manejarErrores } from '../middlewares/errores.middleware.js';
import { ROLES, ROLES_DE_COMPLEJO, permitirRoles } from '../middlewares/rol.middleware.js';

const CLAVE = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
const SIN_PERMISO = { error: true, mensaje: 'No tenés permiso para realizar esta acción.' };

const app = express();
app.get('/panel', autenticar, permitirRoles(...ROLES_DE_COMPLEJO, ROLES.SUPERADMIN), (req, res) => res.json({ ok: true }));
app.get('/sin-autenticar', permitirRoles(ROLES.JUGADOR), (req, res) => res.json({ ok: true }));
app.use(manejarErrores);

const tokenCon = (rol) => jwt.sign(
  { token_type: 'access', jti: randomUUID(), usuario_id: '7', rol },
  CLAVE,
  { algorithm: 'HS256', expiresIn: '30m' },
);

beforeAll(() => {
  process.env.JWT_SIGNING_KEY = CLAVE;
});

describe('Control de acceso por rol', () => {
  test.each([
    [ROLES.DUENO_COMPLEJO, 200],
    [ROLES.OPERADOR_COMPLEJO, 200],
    [ROLES.SUPERADMIN, 200],
    [ROLES.JUGADOR, 403],
  ])('el rol %s recibe %i en una ruta del panel', async (rol, codigo) => {
    const respuesta = await request(app).get('/panel').set('Authorization', `Bearer ${tokenCon(rol)}`);

    expect(respuesta.status).toBe(codigo);
    if (codigo === 403) expect(respuesta.body).toEqual(SIN_PERMISO);
  });

  test('una cuenta con el rol desactivado está autenticada pero sin permisos: 403, no 401', async () => {
    const respuesta = await request(app).get('/panel').set('Authorization', `Bearer ${tokenCon(null)}`);

    expect(respuesta.status).toBe(403);
    expect(respuesta.body).toEqual(SIN_PERMISO);
  });

  test('un rol que no existe en Django no recibe permisos', async () => {
    const respuesta = await request(app).get('/panel').set('Authorization', `Bearer ${tokenCon('ADMIN')}`);

    expect(respuesta.status).toBe(403);
  });

  test('sin token, el 401 de la autenticación llega antes que el control de rol', async () => {
    expect((await request(app).get('/panel')).status).toBe(401);
  });

  test('usado sin autenticar antes, falla como error de configuración y no deja pasar', async () => {
    const consola = jest.spyOn(console, 'error').mockImplementation(() => {});

    const respuesta = await request(app).get('/sin-autenticar');

    expect(respuesta.status).toBe(500);
    expect(respuesta.body).toEqual({ error: true, mensaje: 'Error interno del servidor.' });
    consola.mockRestore();
  });
});

describe('Configuración de permitirRoles', () => {
  test('rechaza al arrancar un rol mal escrito', () => {
    expect(() => permitirRoles('DUENO')).toThrow('DUENO');
  });

  test('rechaza al arrancar una ruta sin roles', () => {
    expect(() => permitirRoles()).toThrow();
  });

  test('los roles coinciden con los de Django', () => {
    expect(Object.values(ROLES).sort()).toEqual(['DUENO_COMPLEJO', 'JUGADOR', 'OPERADOR_COMPLEJO', 'SUPERADMIN']);
  });
});
