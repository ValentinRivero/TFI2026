import { jest } from '@jest/globals';
import request from 'supertest';

const TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo3fQ.firma-de-prueba';

let app;
let salida;

beforeAll(async () => {
  process.env.NODE_ENV = 'production';
  ({ default: app } = await import('../../app.js'));
  process.env.NODE_ENV = 'test';
});

beforeEach(() => {
  salida = jest.spyOn(process.stdout, 'write').mockImplementation(() => true);
});

afterEach(() => {
  salida.mockRestore();
});

const registrado = () => salida.mock.calls.map(([texto]) => String(texto)).join('');

describe('Registro de peticiones (Morgan)', () => {
  test('en producción registra método, ruta y estado de cada petición', async () => {
    await request(app).get('/api/salud');

    expect(registrado()).toMatch(/"GET \/api\/salud HTTP\/1\.1" 200/);
  });

  test('nunca registra el token del encabezado Authorization', async () => {
    await request(app).get('/api/salud').set('Authorization', `Bearer ${TOKEN}`);

    expect(registrado()).not.toContain(TOKEN);
  });
});
