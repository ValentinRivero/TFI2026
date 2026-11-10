import request from 'supertest';

const FRONTEND = 'https://talibre.test';

let app;

beforeAll(async () => {
  process.env.CORS_ALLOWED_ORIGINS = FRONTEND;
  process.env.RATE_LIMIT_VENTANA_MS = '60000';
  process.env.RATE_LIMIT_MAXIMO = '5';
  process.env.NUM_PROXIES = '1';
  ({ default: app } = await import('../../app.js'));
});

const pedirDesde = (ip) => request(app).get('/api/salud').set('Origin', FRONTEND).set('X-Forwarded-For', ip);

describe('Limitador global', () => {
  test('responde 429 con el formato del servicio al superar el máximo por IP', async () => {
    for (let intento = 0; intento < 5; intento += 1) {
      expect((await pedirDesde('203.0.113.10')).status).toBe(200);
    }

    const respuesta = await pedirDesde('203.0.113.10');

    expect(respuesta.status).toBe(429);
    expect(respuesta.body).toEqual({
      error: true,
      mensaje: 'Superaste el límite de solicitudes. Intentá nuevamente más tarde.',
    });
    expect(Number(respuesta.headers['retry-after'])).toBeGreaterThan(0);
    expect(respuesta.headers['access-control-allow-origin']).toBe(FRONTEND);
  });

  test('detrás del proxy cuenta por la IP real de cada cliente', async () => {
    expect((await pedirDesde('203.0.113.10')).status).toBe(429);
    expect((await pedirDesde('198.51.100.20')).status).toBe(200);
  });

  test('informa el cupo con los encabezados estándar y no con los heredados', async () => {
    const respuesta = await pedirDesde('192.0.2.30');

    expect(respuesta.headers.ratelimit).toBeDefined();
    expect(respuesta.headers['x-ratelimit-limit']).toBeUndefined();
  });
});
