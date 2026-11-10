import { randomUUID } from 'node:crypto';

import { jest } from '@jest/globals';
import jwt from 'jsonwebtoken';
import mongoose from 'mongoose';
import request from 'supertest';

import Evento, { TIPOS_EVENTO } from '../models/Evento.js';
import Notificacion, { CATEGORIAS_NOTIFICACION, ESTADOS_NOTIFICACION } from '../models/Notificacion.js';
import { ROLES } from '../middlewares/rol.middleware.js';

const CLAVE = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
const COMPLEJO_PROPIO = 4;
const COMPLEJO_AJENO = 9;

let app;
let fetchSimulado;
let consultas;
let datos;

beforeAll(async () => {
  process.env.JWT_SIGNING_KEY = CLAVE;
  process.env.DJANGO_API_URL = 'http://backend-django:8000';
  ({ default: app } = await import('../../app.js'));
});

const respuestaJson = (status, cuerpo) => new Response(JSON.stringify(cuerpo), { status });

// Django simulado: el usuario 7 administra solo el complejo 4.
const django = async (url) => {
  const ruta = String(url);
  if (ruta.endsWith(`/complejos/${COMPLEJO_PROPIO}/acceso/`)) return respuestaJson(200, { complejo: COMPLEJO_PROPIO });
  return respuestaJson(404, { error: true, detail: 'No se encontró el recurso solicitado.' });
};

beforeEach(() => {
  consultas = [];
  datos = { Evento: [], Notificacion: [], cantidad: 0, porId: null };
  fetchSimulado = jest.spyOn(globalThis, 'fetch').mockImplementation(django);
  // MongoDB simulado a nivel de consulta: se registra cada consulta y se devuelve lo preparado por el test.
  jest.spyOn(mongoose.Query.prototype, 'exec').mockImplementation(async function ejecutar() {
    consultas.push({
      modelo: this.model.modelName, operacion: this.op, filtro: this.getFilter(), opciones: this.getOptions(),
    });
    if (this.op === 'countDocuments') return datos.cantidad;
    if (this.op === 'findOne') return datos.porId;
    return datos[this.model.modelName];
  });
  jest.spyOn(Notificacion.prototype, 'save').mockImplementation(function guardar() {
    return Promise.resolve(this);
  });
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

const tokenDe = (rol, usuarioId = 7) => jwt.sign(
  { token_type: 'access', jti: randomUUID(), usuario_id: String(usuarioId), rol },
  CLAVE,
  { algorithm: 'HS256', expiresIn: '30m' },
);

const como = (rol, usuarioId) => ({ Authorization: `Bearer ${tokenDe(rol, usuarioId)}` });
const consultasDe = (modelo, operacion) => consultas.filter((c) => c.modelo === modelo && c.operacion === operacion);

const evento = (cambios = {}) => new Evento({
  tipo_evento: TIPOS_EVENTO.COMPLEJO_VISTO, complejo_id: COMPLEJO_PROPIO, usuario_id: 31, metadata: { origen: 'mapa' },
  ...cambios,
});

const notificacion = (cambios = {}) => new Notificacion({
  complejo_id: COMPLEJO_PROPIO, categoria: CATEGORIAS_NOTIFICACION.RESERVAS, mensaje: 'Turno cancelado para el martes.',
  ...cambios,
});

describe('GET /api/actividad (panel del complejo)', () => {
  test('lista los eventos del complejo de la página pedida, sin el usuario que los generó', async () => {
    datos.Evento = [evento(), evento({ tipo_evento: TIPOS_EVENTO.GRILLA_CONSULTADA })];
    datos.cantidad = 2;

    const respuesta = await request(app).get('/api/actividad?complejo_id=4').set(como(ROLES.DUENO_COMPLEJO));

    expect(respuesta.status).toBe(200);
    expect(respuesta.body).toMatchObject({ count: 2, next: null, previous: null });
    expect(respuesta.body.results).toHaveLength(2);
    expect(Object.keys(respuesta.body.results[0]).sort()).toEqual(
      ['complejo_id', 'fecha_creacion', 'id', 'metadata', 'tipo_evento'],
    );
    expect(consultasDe('Evento', 'find')[0].filtro).toEqual({ complejo_id: 4, estado: 1 });
    expect(consultasDe('Evento', 'find')[0].opciones).toMatchObject({ sort: { fecha_creacion: -1 }, skip: 0, limit: 20 });
  });

  test('pagina de a 20 con enlaces relativos que conservan los filtros', async () => {
    datos.Evento = [evento()];
    datos.cantidad = 45;

    const respuesta = await request(app).get('/api/actividad?complejo_id=4&page=2').set(como(ROLES.OPERADOR_COMPLEJO));

    expect(consultasDe('Evento', 'find')[0].opciones).toMatchObject({ skip: 20, limit: 20 });
    expect(respuesta.body.next).toBe('/api/actividad?complejo_id=4&page=3&limit=20');
    expect(respuesta.body.previous).toBe('/api/actividad?complejo_id=4&page=1&limit=20');
  });

  test('acepta un tamaño de página propio hasta el máximo', async () => {
    datos.cantidad = 0;

    await request(app).get('/api/actividad?complejo_id=4&limit=50').set(como(ROLES.SUPERADMIN));

    expect(consultasDe('Evento', 'find')[0].opciones.limit).toBe(50);
  });

  test.each([
    ['sin complejo', ''],
    ['complejo inválido', 'complejo_id=abc'],
    ['página cero', 'complejo_id=4&page=0'],
    ['tamaño mayor al máximo', 'complejo_id=4&limit=51'],
  ])('%s responde 400 sin consultar a Django', async (_caso, parametros) => {
    const respuesta = await request(app).get(`/api/actividad?${parametros}`).set(como(ROLES.DUENO_COMPLEJO));

    expect(respuesta.status).toBe(400);
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('una página que no existe responde 404, como en Django', async () => {
    datos.cantidad = 5;

    const respuesta = await request(app).get('/api/actividad?complejo_id=4&page=2').set(como(ROLES.DUENO_COMPLEJO));

    expect(respuesta.status).toBe(404);
    expect(respuesta.body.mensaje).toBe('Página inválida.');
  });

  test('verifica el acceso en Django reenviando el token del usuario', async () => {
    const token = tokenDe(ROLES.DUENO_COMPLEJO);

    await request(app).get('/api/actividad?complejo_id=4').set('Authorization', `Bearer ${token}`);

    const [url, opciones] = fetchSimulado.mock.calls[0];
    expect(String(url)).toBe('http://backend-django:8000/api/complejos/4/acceso/');
    expect(opciones.headers.Authorization).toBe(`Bearer ${token}`);
  });

  test('un complejo que no administra responde el 404 de Django y no consulta MongoDB', async () => {
    const respuesta = await request(app).get('/api/actividad?complejo_id=9').set(como(ROLES.DUENO_COMPLEJO));

    expect(respuesta.status).toBe(404);
    expect(consultas).toHaveLength(0);
  });

  test('un jugador recibe 403 sin consultar a Django', async () => {
    const respuesta = await request(app).get('/api/actividad?complejo_id=4').set(como(ROLES.JUGADOR));

    expect(respuesta.status).toBe(403);
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('sin sesión responde 401', async () => {
    expect((await request(app).get('/api/actividad?complejo_id=4')).status).toBe(401);
  });

  test('si Django no responde, 502', async () => {
    fetchSimulado.mockRejectedValue(new TypeError('fetch failed'));

    expect((await request(app).get('/api/actividad?complejo_id=4').set(como(ROLES.DUENO_COMPLEJO))).status).toBe(502);
  });

  test('si MongoDB no responde, 502', async () => {
    mongoose.Query.prototype.exec.mockRejectedValue(new mongoose.Error.MongooseServerSelectionError('timeout'));

    expect((await request(app).get('/api/actividad?complejo_id=4').set(como(ROLES.DUENO_COMPLEJO))).status).toBe(502);
  });
});

describe('GET /api/actividad/notificaciones (bandeja del complejo)', () => {
  test('devuelve la bandeja del complejo paginada de a 20', async () => {
    datos.Notificacion = [notificacion()];
    datos.cantidad = 21;

    const respuesta = await request(app)
      .get('/api/actividad/notificaciones?complejo_id=4').set(como(ROLES.OPERADOR_COMPLEJO));

    expect(respuesta.status).toBe(200);
    expect(respuesta.body.count).toBe(21);
    expect(respuesta.body.next).toBe('/api/actividad/notificaciones?complejo_id=4&page=2&limit=20');
    expect(consultasDe('Notificacion', 'find')[0].filtro).toEqual(
      { complejo_id: 4, usuario_id: null, estado: { $in: [1, 2] } },
    );
    expect(consultasDe('Notificacion', 'find')[0].opciones).toMatchObject({ skip: 0, limit: 20 });
    expect(consultasDe('Notificacion', 'countDocuments')[0].filtro).toEqual(consultasDe('Notificacion', 'find')[0].filtro);
  });

  test('cada notificación expone su evento resuelto, sin datos de usuarios', async () => {
    const origen = evento({ tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA });
    datos.Notificacion = [notificacion({ evento: origen })];
    datos.cantidad = 1;

    const respuesta = await request(app)
      .get('/api/actividad/notificaciones?complejo_id=4').set(como(ROLES.DUENO_COMPLEJO));

    const [fila] = respuesta.body.results;
    expect(Object.keys(fila).sort()).toEqual(
      ['categoria', 'complejo_id', 'estado', 'evento', 'fecha_creacion', 'id', 'mensaje', 'prioridad'],
    );
    expect(fila.evento).toEqual({
      id: origen.id, tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, complejo_id: 4, fecha_creacion: null,
    });
  });

  test('una notificación sin evento, o con el evento dado de baja, lo muestra en null', async () => {
    datos.Notificacion = [notificacion()];
    datos.cantidad = 1;

    const respuesta = await request(app)
      .get('/api/actividad/notificaciones?complejo_id=4').set(como(ROLES.DUENO_COMPLEJO));

    expect(respuesta.body.results[0].evento).toBeNull();
  });

  test('un jugador no ve la bandeja de un complejo', async () => {
    const respuesta = await request(app).get('/api/actividad/notificaciones?complejo_id=4').set(como(ROLES.JUGADOR));

    expect(respuesta.status).toBe(403);
  });

  test('un complejo ajeno responde 404', async () => {
    const respuesta = await request(app)
      .get('/api/actividad/notificaciones?complejo_id=9').set(como(ROLES.DUENO_COMPLEJO));

    expect(respuesta.status).toBe(404);
    expect(consultas).toHaveLength(0);
  });
});

describe('GET /api/actividad/notificaciones/mias (bandeja propia de cualquier usuario)', () => {
  test.each(Object.values(ROLES))('el rol %s ve sus propias notificaciones', async (rol) => {
    datos.Notificacion = [notificacion({ complejo_id: null, usuario_id: 7 })];
    datos.cantidad = 1;

    const respuesta = await request(app).get('/api/actividad/notificaciones/mias').set(como(rol, 7));

    expect(respuesta.status).toBe(200);
    expect(consultasDe('Notificacion', 'find')[0].filtro).toEqual({ usuario_id: 7, estado: { $in: [1, 2] } });
  });

  test('también una cuenta con el rol desactivado', async () => {
    datos.cantidad = 0;

    expect((await request(app).get('/api/actividad/notificaciones/mias').set(como(null))).status).toBe(200);
  });

  test('el destinatario sale del token: ningún parámetro permite leer las de otra cuenta', async () => {
    datos.cantidad = 0;

    await request(app).get('/api/actividad/notificaciones/mias?usuario_id=99&complejo_id=4').set(como(ROLES.JUGADOR, 7));

    expect(consultasDe('Notificacion', 'find')[0].filtro).toEqual({ usuario_id: 7, estado: { $in: [1, 2] } });
  });

  test('no consulta a Django: no hay complejo que verificar', async () => {
    datos.cantidad = 0;

    await request(app).get('/api/actividad/notificaciones/mias').set(como(ROLES.JUGADOR));

    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('pagina de a 20', async () => {
    datos.cantidad = 30;

    const respuesta = await request(app).get('/api/actividad/notificaciones/mias?page=2').set(como(ROLES.JUGADOR));

    expect(consultasDe('Notificacion', 'find')[0].opciones).toMatchObject({ skip: 20, limit: 20 });
    expect(respuesta.body.previous).toBe('/api/actividad/notificaciones/mias?page=1&limit=20');
  });

  test('sin sesión responde 401', async () => {
    expect((await request(app).get('/api/actividad/notificaciones/mias')).status).toBe(401);
  });
});

describe('PATCH /api/actividad/notificaciones/:id', () => {
  const ID = new mongoose.Types.ObjectId().toString();
  const marcar = (headers, cuerpo = { estado: ESTADOS_NOTIFICACION.LEIDA }) => request(app)
    .patch(`/api/actividad/notificaciones/${ID}`).set(headers).send(cuerpo);

  test('el titular marca como leída su propia notificación', async () => {
    datos.porId = notificacion({ complejo_id: null, usuario_id: 7 });

    const respuesta = await marcar(como(ROLES.JUGADOR, 7));

    expect(respuesta.status).toBe(200);
    expect(respuesta.body.estado).toBe(ESTADOS_NOTIFICACION.LEIDA);
    expect(Notificacion.prototype.save).toHaveBeenCalled();
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('busca solo entre las notificaciones vigentes', async () => {
    datos.porId = notificacion({ complejo_id: null, usuario_id: 7 });

    await marcar(como(ROLES.JUGADOR, 7));

    expect(consultasDe('Notificacion', 'findOne')[0].filtro).toEqual({ _id: ID, estado: { $in: [1, 2] } });
  });

  test('el personal del complejo marca un aviso general del complejo, con acceso verificado en Django', async () => {
    datos.porId = notificacion();

    const respuesta = await marcar(como(ROLES.OPERADOR_COMPLEJO), { estado: ESTADOS_NOTIFICACION.NO_LEIDA });

    expect(respuesta.status).toBe(200);
    expect(String(fetchSimulado.mock.calls[0][0])).toContain('/complejos/4/acceso/');
  });

  test('la notificación personal de otra cuenta responde 404, sin revelar que existe', async () => {
    datos.porId = notificacion({ complejo_id: null, usuario_id: 8 });

    const respuesta = await marcar(como(ROLES.JUGADOR, 7));

    expect(respuesta.status).toBe(404);
    expect(Notificacion.prototype.save).not.toHaveBeenCalled();
  });

  test('un jugador no puede marcar el aviso general de un complejo', async () => {
    datos.porId = notificacion();

    expect((await marcar(como(ROLES.JUGADOR))).status).toBe(404);
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('el aviso de un complejo que no administra responde 404', async () => {
    datos.porId = notificacion({ complejo_id: COMPLEJO_AJENO });

    expect((await marcar(como(ROLES.DUENO_COMPLEJO))).status).toBe(404);
    expect(Notificacion.prototype.save).not.toHaveBeenCalled();
  });

  test('una notificación inexistente o dada de baja responde 404', async () => {
    datos.porId = null;

    expect((await marcar(como(ROLES.JUGADOR))).status).toBe(404);
  });

  test.each([
    ['dar de baja por esta vía', { estado: ESTADOS_NOTIFICACION.BAJA }],
    ['un estado inexistente', { estado: 5 }],
    ['sin estado', {}],
  ])('%s responde 400', async (_caso, cuerpo) => {
    expect((await marcar(como(ROLES.JUGADOR), cuerpo)).status).toBe(400);
  });

  test('un id con formato inválido responde 400 sin consultar MongoDB', async () => {
    const respuesta = await request(app)
      .patch('/api/actividad/notificaciones/no-es-un-id').set(como(ROLES.JUGADOR)).send({ estado: 2 });

    expect(respuesta.status).toBe(400);
    expect(consultas).toHaveLength(0);
  });

  test('sin sesión responde 401', async () => {
    expect((await request(app).patch(`/api/actividad/notificaciones/${ID}`).send({ estado: 2 })).status).toBe(401);
  });

  test('si Django no responde al verificar un aviso del complejo, 502 y no se guarda', async () => {
    datos.porId = notificacion();
    fetchSimulado.mockRejectedValue(new TypeError('fetch failed'));

    expect((await marcar(como(ROLES.DUENO_COMPLEJO))).status).toBe(502);
    expect(Notificacion.prototype.save).not.toHaveBeenCalled();
  });

  test('si MongoDB falla al guardar, 502', async () => {
    datos.porId = notificacion({ complejo_id: null, usuario_id: 7 });
    Notificacion.prototype.save.mockRejectedValue(new mongoose.Error.MongooseServerSelectionError('timeout'));

    expect((await marcar(como(ROLES.JUGADOR, 7))).status).toBe(502);
  });
});
