import { randomUUID } from 'node:crypto';

import { jest } from '@jest/globals';
import jwt from 'jsonwebtoken';
import mongoose from 'mongoose';
import request from 'supertest';

import Evento, { TIPOS_EVENTO } from '../models/Evento.js';
import Notificacion, {
  CATEGORIAS_NOTIFICACION, ESTADOS_NOTIFICACION, PRIORIDADES_NOTIFICACION,
} from '../models/Notificacion.js';

const CLAVE = 'clave-interna-de-prueba-0123456789abcdef0123456789';
const CLAVE_JWT = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
const RUTA = '/api/interno/notificaciones';
const FRONTEND = 'https://talibre.test';

let app;
let guardadas;
let consola;

beforeAll(async () => {
  process.env.INTERNAL_API_KEY = CLAVE;
  process.env.JWT_SIGNING_KEY = CLAVE_JWT;
  process.env.CORS_ALLOWED_ORIGINS = FRONTEND;
  // Cupo global mínimo: la ruta interna no debe consumirlo.
  process.env.RATE_LIMIT_MAXIMO = '3';
  ({ default: app } = await import('../../app.js'));
});

beforeEach(() => {
  process.env.INTERNAL_API_KEY = CLAVE;
  guardadas = [];
  const guardar = function guardar() {
    guardadas.push(this);
    return Promise.resolve(this);
  };
  jest.spyOn(Notificacion.prototype, 'save').mockImplementation(guardar);
  jest.spyOn(Evento.prototype, 'save').mockImplementation(guardar);
  consola = jest.spyOn(console, 'error').mockImplementation(() => {});
  jest.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

const AVISO = {
  complejo_id: 4,
  categoria: CATEGORIAS_NOTIFICACION.RESERVAS,
  prioridad: PRIORIDADES_NOTIFICACION.URGENTE,
  mensaje: 'Un titular dio de baja su cuenta y conserva 1 reserva señada (id 15).',
};

const enviar = (cuerpo, clave = CLAVE) => {
  const pedido = request(app).post(RUTA);
  if (clave !== null) pedido.set('X-Internal-Key', clave);
  return pedido.send(cuerpo);
};

const notificacionGuardada = () => guardadas.find((documento) => documento instanceof Notificacion);
const eventoGuardado = () => guardadas.find((documento) => documento instanceof Evento);

describe('POST /api/interno/notificaciones', () => {
  test('crea un aviso para el panel del complejo, sin leer', async () => {
    const respuesta = await enviar(AVISO);

    expect(respuesta.status).toBe(201);
    const notificacion = notificacionGuardada();
    expect(respuesta.body).toEqual({ id: notificacion.id, evento: null });
    expect(notificacion).toMatchObject({
      ...AVISO, usuario_id: null, evento: null, estado: ESTADOS_NOTIFICACION.NO_LEIDA,
    });
  });

  test('crea un aviso personal para un usuario, con prioridad normal por defecto', async () => {
    const respuesta = await enviar({
      usuario_id: 31, categoria: CATEGORIAS_NOTIFICACION.RESERVAS, mensaje: 'Tu reserva id 20 fue cancelada.',
    });

    expect(respuesta.status).toBe(201);
    expect(notificacionGuardada()).toMatchObject({
      complejo_id: null, usuario_id: 31, prioridad: PRIORIDADES_NOTIFICACION.NORMAL,
    });
  });

  test('con el evento de una reserva realizada, lo registra y lo vincula al aviso del complejo', async () => {
    const respuesta = await enviar({
      ...AVISO,
      prioridad: PRIORIDADES_NOTIFICACION.NORMAL,
      evento: { tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, usuario_id: 31, metadata: { reserva_id: 20 } },
    });

    expect(respuesta.status).toBe(201);
    const evento = eventoGuardado();
    expect(evento).toMatchObject({
      tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, complejo_id: 4, usuario_id: 31, metadata: { reserva_id: 20 },
    });
    expect(String(notificacionGuardada().evento)).toBe(evento.id);
    expect(respuesta.body.evento).toBe(evento.id);
    expect(guardadas.indexOf(evento)).toBeLessThan(guardadas.indexOf(notificacionGuardada()));
  });

  test('ignora los campos que no conoce, como el estado', async () => {
    await enviar({ ...AVISO, estado: ESTADOS_NOTIFICACION.LEIDA, referencias: { reservas: [15] } });

    expect(notificacionGuardada().estado).toBe(ESTADOS_NOTIFICACION.NO_LEIDA);
  });

  describe('autenticación entre servicios', () => {
    test.each([
      ['sin clave', null],
      ['con otra clave del mismo largo', CLAVE.replace(/.$/, 'x')],
      ['con una clave de otro largo', 'corta'],
      ['con la clave en minúsculas cambiadas', CLAVE.toUpperCase()],
    ])('%s responde 401 sin guardar nada', async (_caso, clave) => {
      const respuesta = await enviar(AVISO, clave);

      expect(respuesta.status).toBe(401);
      expect(respuesta.body).toEqual({ error: true, mensaje: 'Credenciales de servicio inválidas.' });
      expect(guardadas).toHaveLength(0);
    });

    test('el token de un usuario, aunque sea superadmin, no sirve', async () => {
      const token = jwt.sign(
        { token_type: 'access', jti: randomUUID(), usuario_id: '1', rol: 'SUPERADMIN' },
        CLAVE_JWT, { algorithm: 'HS256', expiresIn: '5m' },
      );

      const respuesta = await request(app).post(RUTA).set('Authorization', `Bearer ${token}`).send(AVISO);

      expect(respuesta.status).toBe(401);
    });

    test('valida la clave antes que el cuerpo: sin clave no revela qué campos espera', async () => {
      const respuesta = await enviar({}, null);

      expect(respuesta.status).toBe(401);
      expect(respuesta.body.detalles).toBeUndefined();
    });

    test.each([
      ['sin configurar', undefined],
      ['demasiado corta', 'corta'],
    ])('con la clave del servicio %s responde 500 y no acepta ninguna', async (_caso, configurada) => {
      if (configurada === undefined) delete process.env.INTERNAL_API_KEY;
      else process.env.INTERNAL_API_KEY = configurada;

      const respuesta = await enviar(AVISO, configurada ?? CLAVE);

      expect(respuesta.status).toBe(500);
      expect(guardadas).toHaveLength(0);
      expect(consola).toHaveBeenCalled();
    });

    test('la clave no aparece en los registros de un intento fallido', async () => {
      await enviar(AVISO, `${CLAVE}-alterada`);

      const registrado = JSON.stringify([...console.warn.mock.calls, ...consola.mock.calls]);
      expect(registrado).not.toContain(CLAVE);
    });

    test('un navegador no puede enviar la clave: CORS no autoriza ese encabezado', async () => {
      const respuesta = await request(app)
        .options(RUTA)
        .set('Origin', FRONTEND)
        .set('Access-Control-Request-Method', 'POST')
        .set('Access-Control-Request-Headers', 'x-internal-key');

      expect(respuesta.headers['access-control-allow-headers'] ?? '').not.toMatch(/x-internal-key/i);
    });

    test('no consume el cupo del limitador global, que es por IP y compartiría el de los visitantes', async () => {
      for (let intento = 0; intento < 5; intento += 1) {
        expect((await enviar(AVISO)).status).toBe(201);
      }

      expect((await request(app).get('/api/salud')).status).toBe(200);
    });
  });

  describe('validación', () => {
    test.each([
      ['sin destinatario', { ...AVISO, complejo_id: null }, 'complejo_id'],
      ['complejo inválido', { ...AVISO, complejo_id: 'cuatro' }, 'complejo_id'],
      ['usuario inválido', { ...AVISO, usuario_id: 0 }, 'usuario_id'],
      ['sin categoría', { ...AVISO, categoria: undefined }, 'categoria'],
      ['categoría inexistente', { ...AVISO, categoria: 9 }, 'categoria'],
      ['prioridad inexistente', { ...AVISO, prioridad: 3 }, 'prioridad'],
      ['sin mensaje', { ...AVISO, mensaje: '   ' }, 'mensaje'],
      ['mensaje que no es texto', { ...AVISO, mensaje: { $ne: '' } }, 'mensaje'],
      ['mensaje de más de 280 caracteres', { ...AVISO, mensaje: 'a'.repeat(281) }, 'mensaje'],
      ['evento que no es una reserva realizada', { ...AVISO, evento: { tipo_evento: TIPOS_EVENTO.COMPLEJO_VISTO } }, 'evento.tipo_evento'],
      ['evento sin complejo', { ...AVISO, complejo_id: undefined, usuario_id: 31, evento: { tipo_evento: 3 } }, 'complejo_id'],
      ['evento que no es un objeto', { ...AVISO, evento: 'reserva' }, 'evento'],
    ])('%s responde 400 sin guardar nada', async (_caso, cuerpo, campo) => {
      const respuesta = await enviar(cuerpo);

      expect(respuesta.status).toBe(400);
      expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toContain(campo);
      expect(guardadas).toHaveLength(0);
    });

    test.each([
      ['un mensaje con un email', { ...AVISO, mensaje: 'Escribir a juan@correo.com por la seña.' }, 'mensaje'],
      ['metadata con operadores de MongoDB', {
        ...AVISO, evento: { tipo_evento: 3, metadata: { $where: 'sleep(1000)' } },
      }, 'metadata'],
    ])('las reglas del modelo también aplican: %s responde 400', async (_caso, cuerpo, campo) => {
      const respuesta = await enviar(cuerpo);

      expect(respuesta.status).toBe(400);
      expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toContain(campo);
      expect(guardadas).toHaveLength(0);
    });
  });

  test.each([
    ['el aviso', () => Notificacion.prototype.save],
    ['el evento', () => Evento.prototype.save],
  ])('si MongoDB no guarda %s, 502', async (_caso, metodo) => {
    metodo().mockRejectedValue(new mongoose.Error.MongooseServerSelectionError('timeout'));

    const respuesta = await enviar({ ...AVISO, evento: { tipo_evento: 3 } });

    expect(respuesta.status).toBe(502);
  });
});
