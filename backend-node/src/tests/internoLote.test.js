import { jest } from '@jest/globals';
import mongoose from 'mongoose';
import request from 'supertest';

import Evento, { TIPOS_EVENTO } from '../models/Evento.js';
import Notificacion, { CATEGORIAS_NOTIFICACION, PRIORIDADES_NOTIFICACION } from '../models/Notificacion.js';
import { contarFallasExternas, reiniciarFallasExternas } from '../utils/fallasExternas.js';

const CLAVE = 'clave-interna-de-prueba-0123456789abcdef0123456789';
const RUTA = '/api/interno/notificaciones';

let app;
let guardadas;

beforeAll(async () => {
  process.env.INTERNAL_API_KEY = CLAVE;
  process.env.JWT_SIGNING_KEY = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
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
  jest.spyOn(console, 'error').mockImplementation(() => {});
  reiniciarFallasExternas();
});

afterEach(() => {
  jest.restoreAllMocks();
});

const AVISO = {
  complejo_id: 4,
  categoria: CATEGORIAS_NOTIFICACION.RESERVAS,
  prioridad: PRIORIDADES_NOTIFICACION.NORMAL,
  mensaje: 'Complejo Propio: nueva reserva web id 20.',
};

const enviar = (cuerpo) => request(app).post(RUTA).set('X-Internal-Key', CLAVE).send(cuerpo);
const notificaciones = () => guardadas.filter((documento) => documento instanceof Notificacion);

const duplicada = () => Object.assign(new Error('E11000 duplicate key error'), { code: 11000 });

describe('POST /api/interno/notificaciones con varios destinatarios', () => {
  test('crea una notificación personal por usuario, todas con el complejo y el mismo mensaje', async () => {
    const respuesta = await enviar({ ...AVISO, usuarios_ids: [11, 12, 13] });

    expect(respuesta.status).toBe(201);
    expect(notificaciones().map((notificacion) => notificacion.usuario_id)).toEqual([11, 12, 13]);
    expect(notificaciones().every((notificacion) => notificacion.complejo_id === 4)).toBe(true);
    expect(notificaciones().every((notificacion) => notificacion.mensaje === AVISO.mensaje)).toBe(true);
    expect(respuesta.body.ids).toEqual(notificaciones().map((notificacion) => notificacion.id));
    expect(respuesta.body).toMatchObject({ id: notificaciones()[0].id, evento: null, omitidas: 0 });
  });

  test('un usuario repetido en la lista recibe una sola notificación', async () => {
    await enviar({ ...AVISO, usuarios_ids: [11, 11, 12] });

    expect(notificaciones().map((notificacion) => notificacion.usuario_id)).toEqual([11, 12]);
  });

  test('los destinatarios pueden ser solo usuarios, sin complejo', async () => {
    const respuesta = await enviar({ ...AVISO, complejo_id: undefined, usuarios_ids: [1, 2] });

    expect(respuesta.status).toBe(201);
    expect(notificaciones().map((notificacion) => notificacion.complejo_id)).toEqual([null, null]);
  });

  test('el evento se registra una sola vez y vincula todas las notificaciones', async () => {
    const respuesta = await enviar({
      ...AVISO, usuarios_ids: [11, 12],
      evento: { tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, usuario_id: 31, metadata: { reserva_id: 20 } },
    });

    const eventos = guardadas.filter((documento) => documento instanceof Evento);
    expect(eventos).toHaveLength(1);
    expect(notificaciones().map((notificacion) => String(notificacion.evento))).toEqual([eventos[0].id, eventos[0].id]);
    expect(respuesta.body.evento).toBe(eventos[0].id);
  });

  test.each([
    ['una lista vacía', { usuarios_ids: [] }, 'usuarios_ids'],
    ['más usuarios del máximo', { usuarios_ids: Array.from({ length: 51 }, (_, i) => i + 1) }, 'usuarios_ids'],
    ['un id inválido', { usuarios_ids: [11, 0] }, 'usuarios_ids[1]'],
    ['un id que no es número', { usuarios_ids: ['uno'] }, 'usuarios_ids[0]'],
    ['una lista que no es lista', { usuarios_ids: 11 }, 'usuarios_ids'],
    ['usuario y lista a la vez', { usuario_id: 5, usuarios_ids: [1] }, 'usuario_id'],
    ['una clave vacía', { usuario_id: 5, clave_unica: '   ' }, 'clave_unica'],
    ['una clave demasiado larga', { usuario_id: 5, clave_unica: 'c'.repeat(121) }, 'clave_unica'],
    ['una clave que no es texto', { usuario_id: 5, clave_unica: { $ne: '' } }, 'clave_unica'],
  ])('rechaza %s con 400 sin guardar nada', async (_caso, cambios, campo) => {
    const respuesta = await enviar({ ...AVISO, ...cambios });

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toContain(campo);
    expect(guardadas).toHaveLength(0);
  });

  test('un mensaje con un email se rechaza para todos los destinatarios', async () => {
    const respuesta = await enviar({ ...AVISO, usuarios_ids: [1, 2], mensaje: 'Escribir a juan@correo.com' });

    expect(respuesta.status).toBe(400);
    expect(guardadas).toHaveLength(0);
  });
});

describe('Entrada del registro del complejo', () => {
  const REGISTRO = { ambito: 1, mensaje: 'Complejo Propio: se canceló la reserva id 20. (Cancha id 3; Hecho por usuario id 7)' };
  const generales = () => notificaciones().filter((notificacion) => notificacion.usuario_id === null);

  test('se guarda sin destinatario, con su texto y su ámbito, junto a los avisos personales', async () => {
    const respuesta = await enviar({ ...AVISO, usuarios_ids: [11, 12], registro: REGISTRO });

    expect(respuesta.status).toBe(201);
    expect(notificaciones()).toHaveLength(3);
    const [entrada] = generales();
    expect(entrada).toMatchObject({ complejo_id: 4, usuario_id: null, mensaje: REGISTRO.mensaje, ambito: 1 });
    expect(entrada.estado).toBe(1);
    expect(respuesta.body.registro).toBe(entrada.id);
    expect(notificaciones().filter((n) => n.usuario_id !== null).every((n) => n.ambito === null)).toBe(true);
  });

  test('sin destinatarios personales crea solo la entrada del registro, no un aviso general repetido', async () => {
    const respuesta = await enviar({ ...AVISO, registro: { ...REGISTRO, ambito: 2 } });

    expect(respuesta.status).toBe(201);
    expect(notificaciones()).toHaveLength(1);
    expect(notificaciones()[0]).toMatchObject({ usuario_id: null, ambito: 2, mensaje: REGISTRO.mensaje });
    expect(respuesta.body).toMatchObject({ ids: [], registro: notificaciones()[0].id, omitidas: 0 });
  });

  test('el evento de la reserva realizada queda vinculado al registro', async () => {
    await enviar({
      ...AVISO, registro: REGISTRO,
      evento: { tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, usuario_id: 31, metadata: { reserva_id: 20 } },
    });

    const evento = guardadas.find((documento) => documento instanceof Evento);
    expect(String(generales()[0].evento)).toBe(evento.id);
  });

  test.each([
    ['sin ámbito', { mensaje: 'x' }, 'registro.ambito'],
    ['con un ámbito inexistente', { ambito: 3, mensaje: 'x' }, 'registro.ambito'],
    ['sin mensaje', { ambito: 1, mensaje: '  ' }, 'registro.mensaje'],
    ['con un mensaje de más de 280 caracteres', { ambito: 1, mensaje: 'a'.repeat(281) }, 'registro.mensaje'],
  ])('un registro %s responde 400 sin guardar nada', async (_caso, registro, campo) => {
    const respuesta = await enviar({ ...AVISO, registro });

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toContain(campo);
    expect(guardadas).toHaveLength(0);
  });

  test('un registro que no es un objeto o sin complejo responde 400', async () => {
    expect((await enviar({ ...AVISO, registro: 'texto' })).status).toBe(400);
    const sinComplejo = await enviar({ ...AVISO, complejo_id: undefined, usuarios_ids: [1], registro: REGISTRO });

    expect(sinComplejo.status).toBe(400);
    expect(guardadas).toHaveLength(0);
  });

  test('un email en el texto del registro también se rechaza', async () => {
    const respuesta = await enviar({ ...AVISO, registro: { ambito: 1, mensaje: 'Escribir a juan@correo.com' } });

    expect(respuesta.status).toBe(400);
    expect(guardadas).toHaveLength(0);
  });
});

describe('Idempotencia con clave_unica', () => {
  const RECORDATORIO = { ...AVISO, complejo_id: undefined, usuario_id: 31, clave_unica: 'recordatorio-reserva-20' };

  test('guarda la clave en la notificación', async () => {
    await enviar(RECORDATORIO);

    expect(notificaciones()[0].clave_unica).toBe('recordatorio-reserva-20');
  });

  test('sin clave el campo queda en null y nunca se descarta nada', async () => {
    await enviar({ ...RECORDATORIO, clave_unica: undefined });
    await enviar({ ...RECORDATORIO, clave_unica: undefined });

    expect(notificaciones()).toHaveLength(2);
    expect(notificaciones().every((notificacion) => notificacion.clave_unica === null)).toBe(true);
  });

  test('un aviso repetido se ignora: responde 200 y lo informa en omitidas', async () => {
    Notificacion.prototype.save.mockRejectedValueOnce(duplicada());

    const respuesta = await enviar(RECORDATORIO);

    expect(respuesta.status).toBe(200);
    expect(respuesta.body).toEqual({ id: null, ids: [], evento: null, registro: null, omitidas: 1 });
  });

  test('en un lote omite solo a quien ya tenía el aviso y crea el resto', async () => {
    Notificacion.prototype.save
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(duplicada())
      .mockResolvedValueOnce(undefined);

    const respuesta = await enviar({ ...RECORDATORIO, usuario_id: undefined, usuarios_ids: [1, 2, 3] });

    expect(respuesta.status).toBe(201);
    expect(respuesta.body.ids).toHaveLength(2);
    expect(respuesta.body.omitidas).toBe(1);
  });

  test('cualquier otra falla de MongoDB sigue siendo un 502', async () => {
    Notificacion.prototype.save.mockRejectedValueOnce(new mongoose.Error.MongooseServerSelectionError('timeout'));

    const respuesta = await enviar(RECORDATORIO);

    expect(respuesta.status).toBe(502);
  });

  test('un 502 por una falla de MongoDB queda contado como falla de un servicio externo', async () => {
    Notificacion.prototype.save.mockRejectedValueOnce(new mongoose.Error.MongooseServerSelectionError('timeout'));

    await enviar(RECORDATORIO);

    expect(contarFallasExternas(60_000)).toBe(1);
  });

  test('el índice único es por usuario y clave, y solo rige cuando hay clave', () => {
    const indice = Notificacion.schema.indexes().find(([campos]) => campos.clave_unica === 1);

    expect(indice[0]).toEqual({ usuario_id: 1, clave_unica: 1 });
    expect(indice[1]).toMatchObject({ unique: true, partialFilterExpression: { clave_unica: { $type: 'string' } } });
  });
});
