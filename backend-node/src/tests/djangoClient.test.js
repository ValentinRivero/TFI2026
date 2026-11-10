import { jest } from '@jest/globals';
import express from 'express';
import request from 'supertest';

import { ErrorHttp, ErrorServicioExterno, manejarErrores } from '../middlewares/errores.middleware.js';
import { obtenerComplejoPublico, verificarAccesoAComplejo } from '../services/djangoClient.service.js';

const TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNyJ9.firma';
const DETALLE_PUBLICO = {
  id: 4,
  nombre: 'Los Timbós',
  direccion: 'Pasaje Ñandubay 1540',
  latitud: '-29.140000',
  longitud: '-59.260000',
  telefono_contacto: '3777000000',
  canchas: [{ id: 1, nombre: 'Cancha 1' }],
};

const respuesta = (status, cuerpo) => new Response(
  typeof cuerpo === 'string' ? cuerpo : JSON.stringify(cuerpo),
  { status, headers: { 'Content-Type': 'application/json' } },
);

let fetchSimulado;
let consola;

beforeEach(() => {
  process.env.DJANGO_API_URL = 'http://backend-django:8000/api';
  fetchSimulado = jest.spyOn(globalThis, 'fetch');
  consola = jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

const llamada = () => {
  const [url, opciones] = fetchSimulado.mock.calls[0];
  return { url: String(url), opciones };
};

describe('Dirección de Django', () => {
  test.each([
    'http://backend-django:8000/api',
    'http://backend-django:8000/api/',
    'http://backend-django:8000',
    'http://backend-django:8000/',
  ])('con DJANGO_API_URL=%s arma la ruta de la API', async (base) => {
    process.env.DJANGO_API_URL = base;
    fetchSimulado.mockResolvedValue(respuesta(200, DETALLE_PUBLICO));

    await obtenerComplejoPublico(4);

    expect(llamada().url).toBe('http://backend-django:8000/api/complejos/4/');
  });

  test('sin DJANGO_API_URL falla como error de configuración, no como 502', async () => {
    delete process.env.DJANGO_API_URL;

    await expect(obtenerComplejoPublico(4)).rejects.toThrow('DJANGO_API_URL');
    expect(fetchSimulado).not.toHaveBeenCalled();
  });

  test.each(['4/../usuarios', '0', '-1', '1.5', 'abc', null])(
    'rechaza el id de complejo %p sin llamar a Django',
    async (id) => {
      await expect(obtenerComplejoPublico(id)).rejects.toThrow('complejoId');
      await expect(verificarAccesoAComplejo(id, TOKEN)).rejects.toThrow('complejoId');
      expect(fetchSimulado).not.toHaveBeenCalled();
    },
  );
});

describe('obtenerComplejoPublico', () => {
  test('devuelve solo los datos que Node necesita del complejo', async () => {
    fetchSimulado.mockResolvedValue(respuesta(200, DETALLE_PUBLICO));

    expect(await obtenerComplejoPublico(4)).toEqual({
      id: 4, nombre: 'Los Timbós', latitud: -29.14, longitud: -59.26,
    });
  });

  test('es una consulta pública: no reenvía ningún token', async () => {
    fetchSimulado.mockResolvedValue(respuesta(200, DETALLE_PUBLICO));

    await obtenerComplejoPublico(4);

    expect(llamada().opciones.headers).not.toHaveProperty('Authorization');
  });

  test('un complejo inexistente o no habilitado devuelve null', async () => {
    fetchSimulado.mockResolvedValue(respuesta(404, { error: true, detail: 'No encontrado.' }));

    expect(await obtenerComplejoPublico(99)).toBeNull();
  });
});

describe('verificarAccesoAComplejo', () => {
  test('reenvía el token del usuario y resuelve si lo administra', async () => {
    fetchSimulado.mockResolvedValue(respuesta(200, { complejo: 4 }));

    await expect(verificarAccesoAComplejo(4, TOKEN)).resolves.toBeUndefined();
    expect(llamada().url).toBe('http://backend-django:8000/api/complejos/4/acceso/');
    expect(llamada().opciones.headers.Authorization).toBe(`Bearer ${TOKEN}`);
  });

  test.each([
    [401, 'El token es inválido o expiró.'],
    [403, 'No tenés permiso para realizar esta acción.'],
    [404, 'No encontrado.'],
  ])('un %i de Django llega igual al cliente, con el mensaje de Django', async (codigo, detalle) => {
    fetchSimulado.mockResolvedValue(respuesta(codigo, { error: true, detail: detalle }));

    const error = await verificarAccesoAComplejo(4, TOKEN).catch((e) => e);

    expect(error).toBeInstanceOf(ErrorHttp);
    expect(error).not.toBeInstanceOf(ErrorServicioExterno);
    expect([error.status, error.message]).toEqual([codigo, detalle]);
  });

  test('un 401 o 403 sin cuerpo legible usa un mensaje genérico', async () => {
    fetchSimulado.mockResolvedValue(respuesta(403, 'Forbidden'));

    const error = await verificarAccesoAComplejo(4, TOKEN).catch((e) => e);

    expect([error.status, error.message]).toEqual([403, 'No tenés permiso para realizar esta acción.']);
  });
});

describe('Fallas de Django: 502', () => {
  const casos = [
    ['Django responde 500', () => fetchSimulado.mockResolvedValue(respuesta(500, { error: true }))],
    ['Django responde 429', () => fetchSimulado.mockResolvedValue(respuesta(429, { error: true }))],
    ['Django no responde a tiempo', () => fetchSimulado.mockRejectedValue(
      Object.assign(new Error('The operation was aborted due to timeout'), { name: 'TimeoutError' }),
    )],
    ['la red falla', () => fetchSimulado.mockRejectedValue(new TypeError('fetch failed'))],
    ['responde algo que no es JSON', () => fetchSimulado.mockResolvedValue(respuesta(200, '<html>error</html>'))],
  ];

  test.each(casos)('%s en obtenerComplejoPublico', async (_caso, preparar) => {
    preparar();

    await expect(obtenerComplejoPublico(4)).rejects.toBeInstanceOf(ErrorServicioExterno);
  });

  test.each(casos.slice(0, 4))('%s en verificarAccesoAComplejo', async (_caso, preparar) => {
    preparar();

    await expect(verificarAccesoAComplejo(4, TOKEN)).rejects.toBeInstanceOf(ErrorServicioExterno);
  });

  test('cada pedido tiene un tiempo máximo y no sigue redirecciones', async () => {
    fetchSimulado.mockResolvedValue(respuesta(200, DETALLE_PUBLICO));

    await obtenerComplejoPublico(4);

    expect(llamada().opciones.signal).toBeInstanceOf(AbortSignal);
    expect(llamada().opciones.redirect).toBe('error');
  });

  test('registra la causa sin el token del usuario', async () => {
    fetchSimulado.mockRejectedValue(new TypeError(`fetch failed for Bearer ${TOKEN}`));

    await verificarAccesoAComplejo(4, TOKEN).catch(() => {});
    const registrado = consola.mock.calls.flat().map(String).join(' ');

    expect(registrado).toContain('Django');
    expect(registrado).not.toContain(TOKEN);
  });
});

describe('Respuesta HTTP de los errores', () => {
  const app = express();
  app.get('/falla-externa', () => {
    throw new ErrorServicioExterno('Django', new Error('detalle interno 10.0.0.5'));
  });
  app.get('/sin-permiso', () => {
    throw new ErrorHttp(403, 'No tenés permiso para realizar esta acción.');
  });
  app.use(manejarErrores);

  test('un servicio caído responde 502 genérico, sin el detalle interno', async () => {
    const respuestaHttp = await request(app).get('/falla-externa');

    expect(respuestaHttp.status).toBe(502);
    expect(respuestaHttp.body).toEqual({
      error: true,
      mensaje: 'Un servicio necesario no está disponible. Intentá nuevamente en unos minutos.',
    });
  });

  test('un ErrorHttp responde con su código y su mensaje', async () => {
    const respuestaHttp = await request(app).get('/sin-permiso');

    expect(respuestaHttp.status).toBe(403);
    expect(respuestaHttp.body).toEqual({ error: true, mensaje: 'No tenés permiso para realizar esta acción.' });
  });
});
