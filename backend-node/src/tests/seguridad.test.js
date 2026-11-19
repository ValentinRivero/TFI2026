import request from 'supertest';

const FRONTEND = 'https://talibre.test';
const OTRO_SITIO = 'https://sitio-malicioso.test';

let app;

beforeAll(async () => {
  process.env.CORS_ALLOWED_ORIGINS = `${FRONTEND}, http://localhost:5173`;
  process.env.RATE_LIMIT_VENTANA_MS = '60000';
  process.env.RATE_LIMIT_MAXIMO = '1000';
  ({ default: app } = await import('../../app.js'));
});

describe('Encabezados de seguridad (Helmet)', () => {
  test('agrega los encabezados defensivos y oculta la tecnología del servidor', async () => {
    const respuesta = await request(app).get('/api/salud');

    expect(respuesta.headers['x-content-type-options']).toBe('nosniff');
    expect(respuesta.headers['x-frame-options']).toBe('SAMEORIGIN');
    expect(respuesta.headers['strict-transport-security']).toBeDefined();
    expect(respuesta.headers['x-powered-by']).toBeUndefined();
  });

  test('también protege las respuestas de error', async () => {
    const respuesta = await request(app).get('/api/no-existe');

    expect(respuesta.headers['x-content-type-options']).toBe('nosniff');
  });
});

describe('CORS con lista blanca', () => {
  test('autoriza a un origen de la lista', async () => {
    const respuesta = await request(app).get('/api/salud').set('Origin', FRONTEND);

    expect(respuesta.headers['access-control-allow-origin']).toBe(FRONTEND);
    expect(respuesta.headers['access-control-allow-credentials']).toBeUndefined();
  });

  test('ignora los espacios alrededor de cada origen configurado', async () => {
    const respuesta = await request(app).get('/api/salud').set('Origin', 'http://localhost:5173');

    expect(respuesta.headers['access-control-allow-origin']).toBe('http://localhost:5173');
  });

  test('no autoriza a un origen fuera de la lista', async () => {
    const respuesta = await request(app).get('/api/salud').set('Origin', OTRO_SITIO);

    expect(respuesta.headers['access-control-allow-origin']).toBeUndefined();
  });

  test('responde el preflight de un origen permitido con métodos y encabezados acotados', async () => {
    const respuesta = await request(app)
      .options('/api/salud')
      .set('Origin', FRONTEND)
      .set('Access-Control-Request-Method', 'POST')
      .set('Access-Control-Request-Headers', 'Authorization, Content-Type');

    expect(respuesta.status).toBe(204);
    expect(respuesta.headers['access-control-allow-methods']).toBe('GET,POST,PATCH');
    expect(respuesta.headers['access-control-allow-headers']).toBe('Authorization,Content-Type');
  });

  test('el preflight de un origen ajeno no recibe autorización', async () => {
    const respuesta = await request(app)
      .options('/api/salud')
      .set('Origin', OTRO_SITIO)
      .set('Access-Control-Request-Method', 'POST');

    expect(respuesta.headers['access-control-allow-origin']).toBeUndefined();
  });

  test('sin encabezado Origin (llamadas entre servicios) la petición se atiende', async () => {
    expect((await request(app).get('/api/salud')).status).toBe(200);
  });
});
