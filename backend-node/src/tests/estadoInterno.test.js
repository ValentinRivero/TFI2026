import { jest } from '@jest/globals';
import mongoose from 'mongoose';
import request from 'supertest';

import Evento from '../models/Evento.js';
import Notificacion from '../models/Notificacion.js';
import { filtroDeEventosRecientes, medirEstado } from '../services/estadoSistema.service.js';
import { contarFallasExternas, registrarFallaExterna, reiniciarFallasExternas } from '../utils/fallasExternas.js';

const CLAVE = 'clave-interna-de-prueba-0123456789abcdef0123456789';
const RUTA = '/api/interno/estado';

let app;

beforeAll(async () => {
  process.env.INTERNAL_API_KEY = CLAVE;
  process.env.JWT_SIGNING_KEY = 'clave-compartida-de-prueba-con-largo-suficiente-0123456789';
  ({ default: app } = await import('../../app.js'));
});

// MongoDB simulado: la conexión responde al ping y los conteos devuelven números preparados, sin base real.
const simularMongo = ({ conectado = true, ping = () => Promise.resolve({ ok: 1 }), eventos = 15, sinLeer = 3 } = {}) => {
  jest.spyOn(mongoose, 'connection', 'get').mockReturnValue({
    readyState: conectado ? 1 : 0,
    db: { admin: () => ({ ping }) },
  });
  jest.spyOn(Evento, 'countDocuments').mockImplementation(() => Promise.resolve(eventos));
  jest.spyOn(Notificacion, 'countDocuments').mockImplementation(() => Promise.resolve(sinLeer));
};

beforeEach(() => {
  process.env.INTERNAL_API_KEY = CLAVE;
  reiniciarFallasExternas();
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('GET /api/interno/estado', () => {
  test('exige la clave entre servicios', async () => {
    simularMongo();

    expect((await request(app).get(RUTA)).status).toBe(401);
    expect((await request(app).get(RUTA).set('X-Internal-Key', 'otra')).status).toBe(401);
  });

  test('informa ok con las métricas y sin datos personales', async () => {
    simularMongo();

    const respuesta = await request(app).get(RUTA).set('X-Internal-Key', CLAVE);

    expect(respuesta.status).toBe(200);
    expect(respuesta.body).toMatchObject({
      estado: 'ok',
      motivos: [],
      metricas: { eventos_24h: 15, notificaciones_sin_leer: 3, fallas_externas_recientes: 0 },
    });
    expect(Object.keys(respuesta.body.metricas).sort()).toEqual([
      'eventos_24h', 'fallas_externas_recientes', 'latencia_mongo_ms', 'memoria_heap_mb', 'memoria_rss_mb',
      'notificaciones_sin_leer', 'uptime_s',
    ]);
  });

  test('con MongoDB desconectado se informa degradado y no consulta la actividad', async () => {
    simularMongo({ conectado: false });

    const respuesta = await request(app).get(RUTA).set('X-Internal-Key', CLAVE);

    expect(respuesta.status).toBe(200);
    expect(respuesta.body.estado).toBe('degradado');
    expect(respuesta.body.motivos).toEqual(['MongoDB no responde']);
    expect(respuesta.body.metricas).toMatchObject({ latencia_mongo_ms: null, eventos_24h: null });
    expect(Evento.countDocuments).not.toHaveBeenCalled();
  });

  test('un ping que falla cuenta como MongoDB sin respuesta', async () => {
    simularMongo({ ping: () => Promise.reject(new Error('timeout')) });

    const respuesta = await request(app).get(RUTA).set('X-Internal-Key', CLAVE);

    expect(respuesta.body.motivos).toEqual(['MongoDB no responde']);
  });

  test('varias fallas de servicios externos seguidas degradan el estado', async () => {
    simularMongo();
    for (let i = 0; i < 5; i += 1) registrarFallaExterna();

    const respuesta = await request(app).get(RUTA).set('X-Internal-Key', CLAVE);

    expect(respuesta.body.estado).toBe('degradado');
    expect(respuesta.body.motivos).toEqual(['5 fallas de servicios externos en 5 min']);
  });

  test('si falla un conteo, igual responde con la actividad en null', async () => {
    simularMongo();
    jest.spyOn(Evento, 'countDocuments').mockRejectedValue(new Error('caído'));

    const respuesta = await request(app).get(RUTA).set('X-Internal-Key', CLAVE);

    expect(respuesta.status).toBe(200);
    expect(respuesta.body.metricas).toMatchObject({ eventos_24h: null, notificaciones_sin_leer: null });
  });
});

describe('Umbrales del estado', () => {
  test('una latencia de MongoDB por encima del máximo lo degrada', async () => {
    simularMongo();
    process.env.ESTADO_LATENCIA_MONGO_MAXIMA_MS = '10';
    jest.spyOn(performance, 'now').mockReturnValueOnce(0).mockReturnValueOnce(250);

    const estado = await medirEstado();

    delete process.env.ESTADO_LATENCIA_MONGO_MAXIMA_MS;
    expect(estado.motivos).toEqual(['MongoDB tarda 250 ms (máximo 10 ms)']);
  });

  test('la memoria por encima del máximo lo degrada', async () => {
    simularMongo();
    process.env.ESTADO_MEMORIA_MAXIMA_MB = '64';
    jest.spyOn(process, 'memoryUsage').mockReturnValue({ rss: 200 * 1024 * 1024, heapUsed: 50 * 1024 * 1024 });

    const estado = await medirEstado();

    delete process.env.ESTADO_MEMORIA_MAXIMA_MB;
    expect(estado.motivos).toEqual(['memoria de 200 MB (máximo 64 MB)']);
    expect(estado.metricas).toMatchObject({ memoria_rss_mb: 200, memoria_heap_mb: 50 });
  });

  test('las fallas fuera de la ventana no cuentan', () => {
    const ahora = 1_000_000;
    registrarFallaExterna(ahora - 400_000);
    registrarFallaExterna(ahora - 100_000);

    expect(contarFallasExternas(300_000, ahora)).toBe(1);
  });

  test('el registro de fallas tiene un tope', () => {
    for (let i = 0; i < 600; i += 1) registrarFallaExterna(1_000);

    expect(contarFallasExternas(10_000, 1_000)).toBe(500);
  });
});

// `sanitizeFilter` (config/db.js) vuelve literal cualquier operador salvo los marcados con `mongoose.trusted`. Estas
// pruebas castean la consulta como lo hace `exec()`, sin base real: sin la marca, `$gte` se tomaría como un valor.
describe('Consulta de eventos recientes con sanitizeFilter activo', () => {
  const sanitizacionPrevia = mongoose.get('sanitizeFilter');

  beforeAll(() => mongoose.set('sanitizeFilter', true));
  afterAll(() => mongoose.set('sanitizeFilter', sanitizacionPrevia));

  test('el filtro de fecha castea sin error y conserva el operador como fecha', () => {
    const ahora = Date.UTC(2026, 10, 16, 13, 0, 0);
    const consulta = Evento.find(filtroDeEventosRecientes(ahora));

    consulta._castConditions();

    expect(consulta.error()).toBeFalsy();
    const { fecha_creacion: fecha } = consulta.getFilter();
    expect(fecha.$gte).toEqual(new Date(Date.UTC(2026, 10, 15, 13, 0, 0)));
  });

  test('sin la marca de confianza el mismo filtro falla al castear', () => {
    const consulta = Evento.find({ fecha_creacion: { $gte: new Date() } });

    consulta._castConditions();

    expect(consulta.error()).toBeTruthy();
  });
});
