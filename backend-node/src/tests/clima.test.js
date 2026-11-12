import { jest } from '@jest/globals';
import request from 'supertest';

import { cacheDeClima } from '../controllers/externo.controller.js';
import { describirCodigo } from '../services/openMeteo.service.js';

let app;
let fetchSimulado;
let consola;
let django;
let meteo;

beforeAll(async () => {
  process.env.DJANGO_API_URL = 'http://backend-django:8000';
  ({ default: app } = await import('../../app.js'));
});

const respuesta = (status, cuerpo) => new Response(
  typeof cuerpo === 'string' ? cuerpo : JSON.stringify(cuerpo),
  { status, headers: { 'Content-Type': 'application/json' } },
);

const COMPLEJO = {
  id: 1, nombre: 'Complejo El Yacaré', direccion: 'Calle Falsa 123', latitud: '-29.140000', longitud: '-59.260000',
};

const PRONOSTICO = {
  latitude: -29.125,
  longitude: -59.25,
  timezone: 'America/Argentina/Buenos_Aires',
  current_units: { temperature_2m: '°C' },
  current: {
    time: '2026-11-10T15:00', interval: 900, temperature_2m: 27.4, weather_code: 2, wind_speed_10m: 12.6,
    precipitation: 0, is_day: 1,
  },
  daily: {
    time: ['2026-11-10', '2026-11-11', '2026-11-12'],
    weather_code: [2, 61, 95],
    temperature_2m_max: [29.1, 24.3, 22],
    temperature_2m_min: [18.2, 17.5, 16.9],
    precipitation_probability_max: [10, 80, 95],
  },
};

const ruta = (url) => new URL(String(url));

beforeEach(() => {
  cacheDeClima.vaciar();
  django = async () => respuesta(200, COMPLEJO);
  meteo = async () => respuesta(200, PRONOSTICO);
  fetchSimulado = jest.spyOn(globalThis, 'fetch').mockImplementation(async (url, opciones) => (
    ruta(url).hostname === 'api.open-meteo.com' ? meteo(url, opciones) : django(url, opciones)
  ));
  consola = jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

const llamadasA = (host) => fetchSimulado.mock.calls.filter(([url]) => ruta(url).hostname === host);

describe('GET /api/externa/clima/:complejoId', () => {
  test('es pública y devuelve una respuesta liviana con el clima actual y tres días', async () => {
    const res = await request(app).get('/api/externa/clima/1');

    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      complejo: { id: 1, nombre: 'Complejo El Yacaré' },
      actual: {
        fecha_hora: '2026-11-10T15:00',
        temperatura: 27.4,
        codigo_clima: 2,
        descripcion: 'Parcialmente nublado',
        viento_kmh: 12.6,
        precipitacion_mm: 0,
        es_de_dia: true,
      },
      pronostico: [
        { fecha: '2026-11-10', codigo_clima: 2, descripcion: 'Parcialmente nublado', temperatura_max: 29.1, temperatura_min: 18.2, probabilidad_lluvia: 10 },
        { fecha: '2026-11-11', codigo_clima: 61, descripcion: 'Lluvia leve', temperatura_max: 24.3, temperatura_min: 17.5, probabilidad_lluvia: 80 },
        { fecha: '2026-11-12', codigo_clima: 95, descripcion: 'Tormenta', temperatura_max: 22, temperatura_min: 16.9, probabilidad_lluvia: 95 },
      ],
      fuente: 'Open-Meteo.com',
    });
  });

  test('pide a Open-Meteo con las coordenadas del complejo, en hora de Argentina y solo lo que muestra', async () => {
    await request(app).get('/api/externa/clima/1');

    const [[url, opciones]] = llamadasA('api.open-meteo.com');
    const { origin, pathname, searchParams } = ruta(url);
    expect(`${origin}${pathname}`).toBe('https://api.open-meteo.com/v1/forecast');
    expect(Object.fromEntries(searchParams)).toEqual({
      latitude: '-29.14',
      longitude: '-59.26',
      current: 'temperature_2m,weather_code,wind_speed_10m,precipitation,is_day',
      daily: 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
      timezone: 'America/Argentina/Buenos_Aires',
      forecast_days: '3',
    });
    expect(opciones.redirect).toBe('error');
    expect(opciones.signal).toBeInstanceOf(AbortSignal);
  });

  test('no reenvía el token del visitante ni a Django ni a Open-Meteo', async () => {
    await request(app).get('/api/externa/clima/1').set('Authorization', 'Bearer eyJ.un.token');

    fetchSimulado.mock.calls.forEach(([, opciones]) => {
      expect(opciones.headers?.Authorization).toBeUndefined();
    });
    expect(String(llamadasA('backend-django')[0][0])).toBe('http://backend-django:8000/api/complejos/1/');
  });

  test('un complejo inexistente o no habilitado responde 404 sin consultar a Open-Meteo', async () => {
    django = async () => respuesta(404, { error: true, detail: 'No encontrado.' });

    const res = await request(app).get('/api/externa/clima/77');

    expect(res.status).toBe(404);
    expect(res.body).toEqual({ error: true, mensaje: 'No se encontró el complejo.' });
    expect(llamadasA('api.open-meteo.com')).toHaveLength(0);
  });

  test.each(['abc', '0', '-1', '1.5'])('el id %s responde 400 sin consultar a nadie', async (id) => {
    const res = await request(app).get(`/api/externa/clima/${id}`);

    expect(res.status).toBe(400);
    expect(res.body.detalles[0].campo).toBe('complejoId');
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test('si Django no responde, 502 sin consultar a Open-Meteo', async () => {
    django = async () => { throw new TypeError('fetch failed'); };

    expect((await request(app).get('/api/externa/clima/1')).status).toBe(502);
    expect(llamadasA('api.open-meteo.com')).toHaveLength(0);
  });

  test.each([
    ['responde 500', async () => respuesta(500, 'Internal Server Error')],
    ['rechaza el pedido', async () => respuesta(400, { error: true, reason: 'Parameter invalid' })],
    ['limita las solicitudes', async () => respuesta(429, { error: true, reason: 'Too many requests' })],
    ['no está disponible', async () => { throw new TypeError('fetch failed'); }],
    ['tarda demasiado', async () => { throw new DOMException('timeout', 'TimeoutError'); }],
    ['devuelve algo que no es JSON', async () => respuesta(200, '<html>mantenimiento</html>')],
    ['devuelve un JSON sin el clima actual', async () => respuesta(200, { ...PRONOSTICO, current: undefined })],
    ['devuelve null', async () => respuesta(200, 'null')],
    ['devuelve un pronóstico sin días', async () => respuesta(200, {
      ...PRONOSTICO, daily: { ...PRONOSTICO.daily, time: [] },
    })],
    ['devuelve días incompletos', async () => respuesta(200, {
      ...PRONOSTICO, daily: { ...PRONOSTICO.daily, temperature_2m_max: [29.1] },
    })],
    ['devuelve un valor no numérico', async () => respuesta(200, {
      ...PRONOSTICO, current: { ...PRONOSTICO.current, temperature_2m: 'calor' },
    })],
  ])('si Open-Meteo %s, 502 con el mensaje genérico', async (_caso, simulacion) => {
    meteo = simulacion;

    const res = await request(app).get('/api/externa/clima/1');

    expect(res.status).toBe(502);
    expect(res.body).toEqual({
      error: true, mensaje: 'Un servicio necesario no está disponible. Intentá nuevamente en unos minutos.',
    });
    expect(consola).toHaveBeenCalled();
  });

  test('una probabilidad de lluvia sin dato llega como null', async () => {
    meteo = async () => respuesta(200, {
      ...PRONOSTICO, daily: { ...PRONOSTICO.daily, precipitation_probability_max: [null, 80, 95] },
    });

    const res = await request(app).get('/api/externa/clima/1');

    expect(res.status).toBe(200);
    expect(res.body.pronostico[0].probabilidad_lluvia).toBeNull();
  });
});

describe('caché del clima', () => {
  test('un segundo pedido del mismo complejo no vuelve a consultar a Django ni a Open-Meteo', async () => {
    await request(app).get('/api/externa/clima/1');
    const segunda = await request(app).get('/api/externa/clima/1');

    expect(segunda.status).toBe(200);
    expect(fetchSimulado).toHaveBeenCalledTimes(2);
  });

  test('pedidos simultáneos del mismo complejo comparten una sola consulta', async () => {
    const respuestas = await Promise.all([1, 2, 3].map(() => request(app).get('/api/externa/clima/1')));

    expect(respuestas.map((r) => r.status)).toEqual([200, 200, 200]);
    expect(llamadasA('api.open-meteo.com')).toHaveLength(1);
  });

  test('vence a los 15 minutos', async () => {
    const reloj = jest.spyOn(Date, 'now').mockReturnValue(0);
    await request(app).get('/api/externa/clima/1');

    reloj.mockReturnValue(15 * 60 * 1000 - 1);
    await request(app).get('/api/externa/clima/1');
    expect(llamadasA('api.open-meteo.com')).toHaveLength(1);

    reloj.mockReturnValue(15 * 60 * 1000);
    await request(app).get('/api/externa/clima/1');
    expect(llamadasA('api.open-meteo.com')).toHaveLength(2);
  });

  test('cada complejo tiene su propia entrada', async () => {
    await request(app).get('/api/externa/clima/1');
    await request(app).get('/api/externa/clima/2');

    expect(llamadasA('api.open-meteo.com')).toHaveLength(2);
  });

  test.each([
    ['una falla', () => { meteo = async () => respuesta(500, 'error'); }, 502],
    ['un complejo inexistente', () => { django = async () => respuesta(404, {}); }, 404],
  ])('%s no queda guardada: el pedido siguiente vuelve a intentar', async (_caso, preparar, status) => {
    preparar();
    expect((await request(app).get('/api/externa/clima/1')).status).toBe(status);

    django = async () => respuesta(200, COMPLEJO);
    meteo = async () => respuesta(200, PRONOSTICO);
    expect((await request(app).get('/api/externa/clima/1')).status).toBe(200);
  });
});

describe('caché del clima ante consultas superpuestas', () => {
  test('una consulta vieja que falla no borra la que la reemplazó', async () => {
    let fallar;
    meteo = () => new Promise((_resolver, rechazar) => { fallar = () => rechazar(new TypeError('fetch failed')); });
    const vieja = request(app).get('/api/externa/clima/1').then((r) => r);
    await new Promise((resolver) => { setTimeout(resolver, 50); });

    // Vence la entrada y otra consulta ocupa su lugar antes de que la vieja termine.
    cacheDeClima.vaciar();
    meteo = async () => respuesta(200, PRONOSTICO);
    expect((await request(app).get('/api/externa/clima/1')).status).toBe(200);

    fallar();
    expect((await vieja).status).toBe(502);
    await request(app).get('/api/externa/clima/1');
    expect(llamadasA('api.open-meteo.com')).toHaveLength(2);
  });
});

describe('describirCodigo', () => {
  test.each([
    [0, 'Despejado'], [1, 'Mayormente despejado'], [3, 'Nublado'], [45, 'Niebla'], [48, 'Niebla'],
    [53, 'Llovizna'], [56, 'Llovizna helada'], [63, 'Lluvia moderada'], [65, 'Lluvia intensa'],
    [67, 'Lluvia helada'], [73, 'Nevada'], [77, 'Granos de nieve'], [80, 'Chaparrones leves'],
    [82, 'Chaparrones fuertes'], [86, 'Chaparrones de nieve'], [96, 'Tormenta con granizo'], [99, 'Tormenta con granizo'],
  ])('el código WMO %i es "%s"', (codigo, descripcion) => {
    expect(describirCodigo(codigo)).toBe(descripcion);
  });

  test('un código desconocido no rompe la respuesta', () => {
    expect(describirCodigo(42)).toBe('Sin descripción');
  });
});
