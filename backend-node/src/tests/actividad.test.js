import { randomUUID } from 'node:crypto';

import { jest } from '@jest/globals';
import jwt from 'jsonwebtoken';
import mongoose from 'mongoose';
import request from 'supertest';

import Evento, { TIPOS_EVENTO } from '../models/Evento.js';

const CLAVE = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
const DETALLE_COMPLEJO = { id: 4, nombre: 'Los Timbós', latitud: '-29.14', longitud: '-59.26' };

let app;
let fetchSimulado;
let guardados;
let numeroDeIp = 0;

beforeAll(async () => {
  process.env.JWT_SIGNING_KEY = CLAVE;
  process.env.DJANGO_API_URL = 'http://backend-django:8000';
  process.env.NUM_PROXIES = '1';
  process.env.RATE_LIMIT_ACTIVIDAD_MAXIMO = '5';
  ({ default: app } = await import('../../app.js'));
});

beforeEach(() => {
  guardados = [];
  // Una respuesta nueva por llamada: el cuerpo de un Response se puede leer una sola vez.
  fetchSimulado = jest.spyOn(globalThis, 'fetch').mockImplementation(
    async () => new Response(JSON.stringify(DETALLE_COMPLEJO), { status: 200 }),
  );
  jest.spyOn(Evento.prototype, 'save').mockImplementation(function guardar() {
    guardados.push(this);
    return Promise.resolve(this);
  });
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

const tokenDe = (usuarioId) => jwt.sign(
  { token_type: 'access', jti: randomUUID(), usuario_id: String(usuarioId), rol: 'JUGADOR' },
  CLAVE,
  { algorithm: 'HS256', expiresIn: '30m' },
);

// Cada pedido sale de una IP distinta, salvo que el test fije una: el limitador cuenta por IP.
const registrar = (cuerpo, { token, ip } = {}) => {
  numeroDeIp += 1;
  const pedido = request(app).post('/api/actividad').set('X-Forwarded-For', ip ?? `198.51.100.${numeroDeIp % 250}`);
  return (token ? pedido.set('Authorization', `Bearer ${token}`) : pedido).send(cuerpo);
};

const VISITA = { tipo_evento: TIPOS_EVENTO.COMPLEJO_VISTO, complejo_id: 4 };

describe('POST /api/actividad', () => {
  test('un visitante sin sesión registra una visita y recibe solo el id', async () => {
    const respuesta = await registrar(VISITA);

    expect(respuesta.status).toBe(201);
    expect(respuesta.body).toEqual({ id: guardados[0].id });
    expect(guardados[0]).toMatchObject({ tipo_evento: 1, complejo_id: 4, usuario_id: null, metadata: {} });
  });

  test('con sesión, el usuario sale del token', async () => {
    await registrar({ tipo_evento: TIPOS_EVENTO.GRILLA_CONSULTADA, complejo_id: 4, metadata: { fecha: '2026-11-24' } }, {
      token: tokenDe(12),
    });

    expect(guardados[0]).toMatchObject({ tipo_evento: 2, usuario_id: 12, metadata: { fecha: '2026-11-24' } });
  });

  test('nadie puede atribuirle un evento a otra cuenta enviando usuario_id en el cuerpo', async () => {
    await registrar({ ...VISITA, usuario_id: 99 }, { token: tokenDe(12) });
    await registrar({ ...VISITA, usuario_id: 99 });

    expect(guardados.map((evento) => evento.usuario_id)).toEqual([12, null]);
  });

  test('un token inválido o vencido no bloquea la visita: se registra como anónima', async () => {
    const respuesta = await registrar(VISITA, { token: 'no-es-un-jwt' });

    expect(respuesta.status).toBe(201);
    expect(guardados[0].usuario_id).toBeNull();
  });

  test('no acepta "reserva realizada": ese evento solo lo emite Django', async () => {
    const respuesta = await registrar({ tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, complejo_id: 4 }, {
      token: tokenDe(12),
    });

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.detalles).toEqual([
      { campo: 'tipo_evento', mensaje: 'Solo se registran visitas al complejo (1) y consultas de la grilla (2).' },
    ]);
    expect(fetchSimulado).not.toHaveBeenCalled();
    expect(guardados).toHaveLength(0);
  });

  test.each([
    ['sin tipo', { complejo_id: 4 }, 'tipo_evento'],
    ['tipo no numérico', { tipo_evento: 'visita', complejo_id: 4 }, 'tipo_evento'],
    ['sin complejo', { tipo_evento: 1 }, 'complejo_id'],
    ['complejo cero', { tipo_evento: 1, complejo_id: 0 }, 'complejo_id'],
    ['complejo que intenta otra ruta', { tipo_evento: 1, complejo_id: '4/../usuarios' }, 'complejo_id'],
  ])('%s responde 400 sin consultar a Django', async (_caso, cuerpo, campo) => {
    const respuesta = await registrar(cuerpo);

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toContain(campo);
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test.each([
    ['una lista', ['a']],
    ['operadores de MongoDB', { $where: 'sleep(1000)' }],
    ['más de 2 KB', { relleno: 'x'.repeat(2100) }],
  ])('metadata con %s responde 400 con el detalle del modelo', async (_caso, metadata) => {
    const respuesta = await registrar({ ...VISITA, metadata });

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.mensaje).toBe('Datos inválidos.');
    expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toEqual(['metadata']);
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('un complejo inexistente o no habilitado responde 404 y no se guarda nada', async () => {
    fetchSimulado.mockResolvedValue(new Response('{"error": true, "detail": "No encontrado."}', { status: 404 }));

    const respuesta = await registrar(VISITA);

    expect(respuesta.status).toBe(404);
    expect(respuesta.body).toEqual({ error: true, mensaje: 'No se encontró el complejo.' });
    expect(guardados).toHaveLength(0);
  });

  test('consulta a Django sin reenviar el token del visitante', async () => {
    await registrar(VISITA, { token: tokenDe(12) });

    const [url, opciones] = fetchSimulado.mock.calls[0];
    expect(String(url)).toBe('http://backend-django:8000/api/complejos/4/');
    expect(opciones.headers).not.toHaveProperty('Authorization');
  });

  test('si Django no responde, 502 y no se guarda nada', async () => {
    fetchSimulado.mockRejectedValue(new TypeError('fetch failed'));

    const respuesta = await registrar(VISITA);

    expect(respuesta.status).toBe(502);
    expect(guardados).toHaveLength(0);
  });

  test('si MongoDB no responde al guardar, 502', async () => {
    Evento.prototype.save.mockRejectedValue(new mongoose.Error.MongooseServerSelectionError('connection timed out'));

    const respuesta = await registrar(VISITA);

    expect(respuesta.status).toBe(502);
    expect(respuesta.body.mensaje).toBe('Un servicio necesario no está disponible. Intentá nuevamente en unos minutos.');
  });

  test('tiene un limitador propio, más estricto que el global', async () => {
    const ip = '203.0.113.77';
    for (let intento = 0; intento < 5; intento += 1) {
      expect((await registrar(VISITA, { ip })).status).toBe(201);
    }

    const respuesta = await registrar(VISITA, { ip });

    expect(respuesta.status).toBe(429);
    expect(guardados).toHaveLength(5);
  });
});
