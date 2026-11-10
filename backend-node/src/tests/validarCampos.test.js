import express from 'express';
import { body, query } from 'express-validator';
import request from 'supertest';

import { validarCampos } from '../middlewares/validarCampos.middleware.js';

const app = express();
app.use(express.json());
app.post(
  '/eventos',
  body('tipo_evento').isIn(['VISITA_COMPLEJO', 'RESERVA_REALIZADA']).withMessage('Tipo de evento no admitido.'),
  body('complejo_id')
    .isInt({ min: 1 }).withMessage('Debe ser un número entero positivo.')
    .toInt(),
  body('metadata.cancha_id').optional().isInt({ min: 1 }),
  validarCampos,
  (req, res) => res.status(201).json({ recibido: req.body }),
);
app.get(
  '/eventos',
  query('page').optional().isInt({ min: 1 }).withMessage('Debe ser un número de página válido.'),
  validarCampos,
  (req, res) => res.json({ ok: true }),
);

describe('Validación de campos', () => {
  test('con datos válidos sigue y entrega los valores ya convertidos', async () => {
    const respuesta = await request(app).post('/eventos').send({ tipo_evento: 'VISITA_COMPLEJO', complejo_id: '4' });

    expect(respuesta.status).toBe(201);
    expect(respuesta.body.recibido.complejo_id).toBe(4);
  });

  test('responde 400 con un detalle por campo inválido', async () => {
    const respuesta = await request(app).post('/eventos').send({ tipo_evento: 'BORRAR_TODO', complejo_id: 'abc' });

    expect(respuesta.status).toBe(400);
    expect(respuesta.body).toEqual({
      error: true,
      mensaje: 'Datos inválidos.',
      detalles: [
        { campo: 'tipo_evento', mensaje: 'Tipo de evento no admitido.' },
        { campo: 'complejo_id', mensaje: 'Debe ser un número entero positivo.' },
      ],
    });
  });

  test('informa un solo error por campo aunque falle más de una regla', async () => {
    const respuesta = await request(app).post('/eventos').send({ tipo_evento: 'VISITA_COMPLEJO' });

    expect(respuesta.body.detalles.filter((detalle) => detalle.campo === 'complejo_id')).toHaveLength(1);
  });

  test('nunca devuelve el valor enviado, para no reflejar datos del cliente', async () => {
    const respuesta = await request(app).post('/eventos').send({
      tipo_evento: '<script>alert(1)</script>', complejo_id: 4,
    });

    expect(JSON.stringify(respuesta.body)).not.toContain('<script>');
  });

  test('nombra los campos anidados con su ruta completa', async () => {
    const respuesta = await request(app).post('/eventos').send({
      tipo_evento: 'VISITA_COMPLEJO', complejo_id: 4, metadata: { cancha_id: 'x' },
    });

    expect(respuesta.body.detalles).toEqual([{ campo: 'metadata.cancha_id', mensaje: 'Valor inválido.' }]);
  });

  test('valida también los parámetros de consulta', async () => {
    const respuesta = await request(app).get('/eventos?page=0');

    expect(respuesta.status).toBe(400);
    expect(respuesta.body.detalles).toEqual([{ campo: 'page', mensaje: 'Debe ser un número de página válido.' }]);
  });
});
