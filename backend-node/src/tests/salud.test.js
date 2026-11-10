import { jest } from '@jest/globals';
import request from 'supertest';

import app from '../../app.js';

describe('GET /api/salud', () => {
  test('responde 200 sin autenticación', async () => {
    const respuesta = await request(app).get('/api/salud');

    expect(respuesta.status).toBe(200);
    expect(respuesta.body).toEqual({ estado: 'ok' });
  });
});

describe('Formato de errores', () => {
  test('una ruta inexistente responde 404 con el formato del servicio', async () => {
    const respuesta = await request(app).get('/api/no-existe');

    expect(respuesta.status).toBe(404);
    expect(respuesta.body).toEqual({ error: true, mensaje: 'No se encontró el recurso solicitado.' });
  });

  test('un método no definido sobre una ruta existente también responde 404', async () => {
    const respuesta = await request(app).delete('/api/salud');

    expect(respuesta.status).toBe(404);
    expect(respuesta.body.error).toBe(true);
  });

  test('un JSON mal formado responde 400 sin exponer el error del parser', async () => {
    const respuesta = await request(app)
      .post('/api/salud')
      .set('Content-Type', 'application/json')
      .send('{"tipo_evento": ');

    expect(respuesta.status).toBe(400);
    expect(respuesta.body).toEqual({ error: true, mensaje: 'El cuerpo de la solicitud no es un JSON válido.' });
  });

  test('un cuerpo demasiado grande responde 413', async () => {
    const respuesta = await request(app)
      .post('/api/salud')
      .set('Content-Type', 'application/json')
      .send(JSON.stringify({ metadata: 'x'.repeat(20 * 1024) }));

    expect(respuesta.status).toBe(413);
    expect(respuesta.body).toEqual({ error: true, mensaje: 'El cuerpo de la solicitud supera el tamaño permitido.' });
  });

  test('un error de validación del modelo responde 400 con un detalle por campo, sin el valor recibido', async () => {
    const { manejarErrores } = await import('../middlewares/errores.middleware.js');
    const { default: Evento } = await import('../models/Evento.js');
    const error = new Evento({ tipo_evento: '<script>', complejo_id: undefined, metadata: ['x'] }).validateSync();
    const respuesta = { status: jest.fn().mockReturnThis(), json: jest.fn() };

    manejarErrores(error, {}, respuesta, () => {});

    expect(respuesta.status).toHaveBeenCalledWith(400);
    const [cuerpo] = respuesta.json.mock.calls[0];
    expect(cuerpo.mensaje).toBe('Datos inválidos.');
    expect(cuerpo.detalles).toEqual(expect.arrayContaining([
      { campo: 'tipo_evento', mensaje: 'Valor inválido.' },
      { campo: 'complejo_id', mensaje: 'El complejo es obligatorio.' },
      { campo: 'metadata', mensaje: 'metadata debe ser un objeto.' },
    ]));
    expect(JSON.stringify(cuerpo)).not.toContain('<script>');
  });

  test('un error no previsto responde 500 genérico y no filtra el detalle', async () => {
    const { manejarErrores } = await import('../middlewares/errores.middleware.js');
    const respuesta = { status: jest.fn().mockReturnThis(), json: jest.fn() };
    const consola = jest.spyOn(console, 'error').mockImplementation(() => {});

    manejarErrores(new Error('conexión a 10.0.0.5 rechazada'), {}, respuesta, () => {});

    expect(respuesta.status).toHaveBeenCalledWith(500);
    expect(respuesta.json).toHaveBeenCalledWith({ error: true, mensaje: 'Error interno del servidor.' });
    expect(consola).toHaveBeenCalled();
    consola.mockRestore();
  });
});
