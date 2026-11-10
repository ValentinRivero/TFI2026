import { randomUUID } from 'node:crypto';

import { jest } from '@jest/globals';
import jwt from 'jsonwebtoken';
import mongoose from 'mongoose';
import request from 'supertest';

import { ROLES } from '../middlewares/rol.middleware.js';

const CLAVE = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
const RUTA = '/api/reportes-aux/visitas';

let app;
let fetchSimulado;
let pipelines;
let grupos;

beforeAll(async () => {
  process.env.JWT_SIGNING_KEY = CLAVE;
  process.env.DJANGO_API_URL = 'http://backend-django:8000';
  ({ default: app } = await import('../../app.js'));
});

const respuestaJson = (status, cuerpo) => new Response(JSON.stringify(cuerpo), { status });

beforeEach(() => {
  pipelines = [];
  grupos = [];
  // Django simulado: el usuario administra solo el complejo 4.
  fetchSimulado = jest.spyOn(globalThis, 'fetch').mockImplementation(async (url) => (
    String(url).endsWith('/complejos/4/acceso/')
      ? respuestaJson(200, { complejo: 4 })
      : respuestaJson(404, { error: true, detail: 'No se encontró el recurso solicitado.' })
  ));
  jest.spyOn(mongoose.Aggregate.prototype, 'exec').mockImplementation(async function ejecutar() {
    pipelines.push({ modelo: this.model().modelName, etapas: this.pipeline() });
    return grupos;
  });
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

const como = (rol) => ({
  Authorization: `Bearer ${jwt.sign(
    { token_type: 'access', jti: randomUUID(), usuario_id: '7', rol }, CLAVE, { algorithm: 'HS256', expiresIn: '30m' },
  )}`,
});

const pedir = (parametros, rol = ROLES.DUENO_COMPLEJO) => request(app)
  .get(`${RUTA}?${new URLSearchParams(parametros)}`).set(como(rol));

const RANGO = { complejo_id: 4, fecha_desde: '2026-11-01', fecha_hasta: '2026-11-03' };

describe('GET /api/reportes-aux/visitas', () => {
  test('suma visitas y consultas por día, con los días sin actividad en cero', async () => {
    grupos = [
      { _id: { fecha: '2026-11-01', tipo: 1 }, cantidad: 5 },
      { _id: { fecha: '2026-11-01', tipo: 2 }, cantidad: 3 },
      { _id: { fecha: '2026-11-03', tipo: 1 }, cantidad: 2 },
    ];

    const respuesta = await pedir(RANGO);

    expect(respuesta.status).toBe(200);
    expect(respuesta.body).toEqual({
      filtros: { complejo_id: 4, fecha_desde: '2026-11-01', fecha_hasta: '2026-11-03' },
      totales: { visitas: 7, consultas_grilla: 3 },
      por_dia: [
        { fecha: '2026-11-01', visitas: 5, consultas_grilla: 3 },
        { fecha: '2026-11-02', visitas: 0, consultas_grilla: 0 },
        { fecha: '2026-11-03', visitas: 2, consultas_grilla: 0 },
      ],
    });
  });

  test('un rango sin actividad devuelve todos los días en cero', async () => {
    const respuesta = await pedir({ complejo_id: 4, fecha_desde: '2026-11-10', fecha_hasta: '2026-11-11' });

    expect(respuesta.body.totales).toEqual({ visitas: 0, consultas_grilla: 0 });
    expect(respuesta.body.por_dia).toEqual([
      { fecha: '2026-11-10', visitas: 0, consultas_grilla: 0 },
      { fecha: '2026-11-11', visitas: 0, consultas_grilla: 0 },
    ]);
  });

  test('ignora los eventos que no son visitas ni consultas, como "reserva realizada"', async () => {
    grupos = [{ _id: { fecha: '2026-11-01', tipo: 3 }, cantidad: 9 }];

    const respuesta = await pedir(RANGO);

    expect(respuesta.body.totales).toEqual({ visitas: 0, consultas_grilla: 0 });
  });

  test('agrupa en MongoDB por día de Argentina, solo eventos activos del complejo y dentro del rango', async () => {
    await pedir(RANGO);

    const [{ modelo, etapas }] = pipelines;
    expect(modelo).toBe('Evento');
    expect(etapas[0]).toEqual({
      $match: {
        complejo_id: 4,
        estado: 1,
        tipo_evento: { $in: [1, 2] },
        fecha_creacion: { $gte: new Date('2026-11-01T03:00:00.000Z'), $lt: new Date('2026-11-04T03:00:00.000Z') },
      },
    });
    expect(etapas[1].$group._id.fecha.$dateToString).toEqual({
      format: '%Y-%m-%d', date: '$fecha_creacion', timezone: '-03:00',
    });
    expect(etapas[1].$group.cantidad).toEqual({ $sum: 1 });
  });

  test('una visita a las 23:30 de Argentina cuenta en ese día, aunque en UTC ya sea el siguiente', async () => {
    await pedir({ complejo_id: 4, fecha_desde: '2026-11-30', fecha_hasta: '2026-11-30' });

    const { fecha_creacion: rango } = pipelines[0].etapas[0].$match;
    const visita = new Date('2026-12-01T02:30:00.000Z');
    expect(visita >= rango.$gte && visita < rango.$lt).toBe(true);
  });

  test('acepta un rango de 366 días, ambos extremos incluidos', async () => {
    const respuesta = await pedir({ complejo_id: 4, fecha_desde: '2028-01-01', fecha_hasta: '2028-12-31' });

    expect(respuesta.status).toBe(200);
    expect(respuesta.body.por_dia).toHaveLength(366);
  });

  test.each([
    ['sin complejo', { fecha_desde: '2026-11-01', fecha_hasta: '2026-11-02' }, 'complejo_id'],
    ['complejo inválido', { ...RANGO, complejo_id: 'abc' }, 'complejo_id'],
    ['complejo repetido', [['complejo_id', '4'], ['complejo_id', '9'], ['fecha_desde', '2026-11-01'], ['fecha_hasta', '2026-11-02']], 'complejo_id'],
    ['fecha repetida', [['complejo_id', '4'], ['fecha_desde', '2026-11-01'], ['fecha_desde', '2026-11-02'], ['fecha_hasta', '2026-11-02']], 'fecha_desde'],
    ['sin fecha_desde', { complejo_id: 4, fecha_hasta: '2026-11-02' }, 'fecha_desde'],
    ['sin fecha_hasta', { complejo_id: 4, fecha_desde: '2026-11-02' }, 'fecha_hasta'],
    ['formato distinto de AAAA-MM-DD', { ...RANGO, fecha_desde: '01/11/2026' }, 'fecha_desde'],
    ['fecha con hora', { ...RANGO, fecha_desde: '2026-11-01T00:00:00Z' }, 'fecha_desde'],
    ['fecha inexistente', { ...RANGO, fecha_hasta: '2026-02-30' }, 'fecha_hasta'],
    ['hasta anterior a desde', { ...RANGO, fecha_desde: '2026-11-05' }, 'fecha_hasta'],
    ['más de 366 días', { complejo_id: 4, fecha_desde: '2026-01-01', fecha_hasta: '2027-01-02' }, 'fecha_hasta'],
  ])('%s responde 400 sin consultar a Django ni a MongoDB', async (_caso, parametros, campo) => {
    const respuesta = await pedir(parametros);

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.detalles.map((detalle) => detalle.campo)).toContain(campo);
    expect(fetchSimulado).not.toHaveBeenCalled();
    expect(pipelines).toHaveLength(0);
  });

  test('los mensajes de fecha coinciden con los de Django', async () => {
    const formato = await pedir({ ...RANGO, fecha_desde: 'ayer' });
    const orden = await pedir({ ...RANGO, fecha_desde: '2026-11-05' });
    const largo = await pedir({ complejo_id: 4, fecha_desde: '2026-01-01', fecha_hasta: '2027-01-02' });

    expect(formato.body.detalles).toContainEqual({ campo: 'fecha_desde', mensaje: 'Usá el formato AAAA-MM-DD.' });
    expect(orden.body.detalles).toContainEqual(
      { campo: 'fecha_hasta', mensaje: 'Debe ser igual o posterior a fecha_desde.' },
    );
    expect(largo.body.detalles).toContainEqual(
      { campo: 'fecha_hasta', mensaje: 'El rango del reporte abarca como máximo 366 días.' },
    );
  });

  test('reenvía el token a Django para verificar el acceso', async () => {
    const encabezado = como(ROLES.OPERADOR_COMPLEJO);

    await request(app).get(`${RUTA}?${new URLSearchParams(RANGO)}`).set(encabezado);

    const [url, opciones] = fetchSimulado.mock.calls[0];
    expect(String(url)).toBe('http://backend-django:8000/api/complejos/4/acceso/');
    expect(opciones.headers.Authorization).toBe(encabezado.Authorization);
  });

  test.each([ROLES.DUENO_COMPLEJO, ROLES.OPERADOR_COMPLEJO, ROLES.SUPERADMIN])('el rol %s accede', async (rol) => {
    expect((await pedir(RANGO, rol)).status).toBe(200);
  });

  test('un complejo ajeno responde 404 sin consultar MongoDB', async () => {
    const respuesta = await pedir({ ...RANGO, complejo_id: 9 });

    expect(respuesta.status).toBe(404);
    expect(pipelines).toHaveLength(0);
  });

  test.each([ROLES.JUGADOR, null])('el rol %s recibe 403 sin consultar a Django', async (rol) => {
    expect((await pedir(RANGO, rol)).status).toBe(403);
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('sin sesión responde 401', async () => {
    expect((await request(app).get(`${RUTA}?${new URLSearchParams(RANGO)}`)).status).toBe(401);
  });

  test('si Django no responde, 502', async () => {
    fetchSimulado.mockRejectedValue(new TypeError('fetch failed'));

    expect((await pedir(RANGO)).status).toBe(502);
  });

  test('si MongoDB no responde, 502 sin detalles internos', async () => {
    mongoose.Aggregate.prototype.exec.mockRejectedValue(new mongoose.Error.MongooseServerSelectionError('timeout'));

    const respuesta = await pedir(RANGO);

    expect(respuesta.status).toBe(502);
    expect(JSON.stringify(respuesta.body)).not.toContain('timeout');
  });
});
