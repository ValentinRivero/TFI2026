import { describe, expect, test } from 'vitest';
import { ErrorApi, normalizarError, normalizarRespuesta } from './errores.js';

describe('errores de Django', () => {
  test('detail de texto', () => {
    const error = normalizarRespuesta(401, { error: true, detail: 'Email o contraseña incorrectos.' });

    expect(error).toBeInstanceOf(ErrorApi);
    expect(error.status).toBe(401);
    expect(error.mensaje).toBe('Email o contraseña incorrectos.');
    expect(error.campos).toEqual({});
  });

  test('detail por campo con listas de mensajes', () => {
    const error = normalizarRespuesta(400, {
      error: true,
      detail: { email: ['Ya existe una cuenta con ese email.'], password: ['Muy corta.', 'Muy común.'] },
    });

    expect(error.campos).toEqual({ email: 'Ya existe una cuenta con ese email.', password: 'Muy corta. Muy común.' });
    expect(error.mensaje).toBe('Revisá los datos ingresados.');
  });

  test('un error general entre los campos pasa a ser el mensaje', () => {
    const error = normalizarRespuesta(400, { detail: { non_field_errors: ['Indicá al menos un campo.'], nombre: ['Obligatorio.'] } });

    expect(error.mensaje).toBe('Indicá al menos un campo.');
    expect(error.campos).toEqual({ nombre: 'Obligatorio.' });
  });

  test('campos anidados se aplanan con su ruta', () => {
    const error = normalizarRespuesta(400, { detail: { cancha: { nombre: ['Repetido.'] }, items: [{ id: ['Inválido.'] }] } });

    expect(error.campos['cancha.nombre']).toBe('Repetido.');
    expect(error.campos['items.0.id']).toBe('Inválido.');
  });

  test('detail como lista de textos', () => {
    expect(normalizarRespuesta(400, { detail: ['Primero.', 'Segundo.'] }).mensaje).toBe('Primero. Segundo.');
  });

  test('un 409 conserva requiere_confirmacion y conflictos', () => {
    const conflictos = { cantidad: 2, reservas: [{ id: 1 }], turnos_fijos: [] };
    const error = normalizarRespuesta(409, {
      error: true, detail: 'Hay reservas afectadas.', requiere_confirmacion: true, conflictos,
    });

    expect(error.status).toBe(409);
    expect(error.mensaje).toBe('Hay reservas afectadas.');
    expect(error.extra).toEqual({ requiere_confirmacion: true, conflictos });
  });

  test('un 409 sin confirmación posible no trae requiere_confirmacion', () => {
    expect(normalizarRespuesta(409, { detail: 'El turno ya está reservado.' }).extra).toEqual({});
  });
});

describe('errores de Node', () => {
  test('mensaje y detalles por campo', () => {
    const error = normalizarRespuesta(400, {
      error: true,
      mensaje: 'Datos inválidos.',
      detalles: [
        { campo: 'complejo_id', mensaje: 'Debe ser un número entero positivo.' },
        { campo: 'metadata.cancha_id', mensaje: 'Inválido.' },
      ],
    });

    expect(error.mensaje).toBe('Datos inválidos.');
    expect(error.campos).toEqual({
      complejo_id: 'Debe ser un número entero positivo.', 'metadata.cancha_id': 'Inválido.',
    });
    expect(error.extra).toEqual({});
  });

  test('un error sin detalles', () => {
    const error = normalizarRespuesta(404, { error: true, mensaje: 'No se encontró el complejo.' });

    expect(error.mensaje).toBe('No se encontró el complejo.');
    expect(error.campos).toEqual({});
  });

  test('ignora detalles mal formados', () => {
    const error = normalizarRespuesta(400, { mensaje: 'Datos inválidos.', detalles: [null, { campo: 'a' }, 'x', { mensaje: 'b' }] });

    expect(error.campos).toEqual({});
  });
});

describe('mensajes generales por código', () => {
  test.each([
    [400, 'Revisá los datos ingresados.'],
    [401, 'Tenés que iniciar sesión para continuar.'],
    [403, 'No tenés permiso para realizar esta acción.'],
    [404, 'No encontramos lo que buscás.'],
    [409, 'La operación entra en conflicto con otra existente.'],
  ])('un %i sin texto del backend', (status, mensaje) => {
    expect(normalizarRespuesta(status, {}).mensaje).toBe(mensaje);
  });

  test('un 403 con texto del backend lo conserva', () => {
    expect(normalizarRespuesta(403, { detail: 'La cuenta está suspendida.' }).mensaje).toBe('La cuenta está suspendida.');
  });

  test('un 429 usa siempre el mensaje general, aunque el backend diga otra cosa', () => {
    const error = normalizarRespuesta(429, { detail: 'Request was throttled. Expected available in 41 seconds.' });

    expect(error.mensaje).toBe('Hiciste demasiadas solicitudes. Esperá un momento e intentá nuevamente.');
    expect(error.status).toBe(429);
  });

  test.each([500, 502, 503, 504])('un %i usa el mensaje de servicio no disponible', (status) => {
    const error = normalizarRespuesta(status, { mensaje: 'Un servicio necesario no está disponible.' });

    expect(error.mensaje).toBe('El servicio no está disponible por el momento. Intentá nuevamente en unos minutos.');
  });

  test.each([null, undefined, 'Bad Gateway', '<html>502</html>', 42, []])('un cuerpo que no es de la API (%s)', (cuerpo) => {
    const error = normalizarRespuesta(502, cuerpo);

    expect(error.status).toBe(502);
    expect(error.campos).toEqual({});
    expect(error.extra).toEqual({});
  });

  test('un código sin mensaje propio usa el general', () => {
    expect(normalizarRespuesta(418, {}).mensaje).toBe('No pudimos completar la operación. Intentá nuevamente.');
  });
});

describe('normalizarError', () => {
  test('una respuesta de Axios', () => {
    const error = normalizarError({ response: { status: 400, data: { detail: { email: ['Inválido.'] } } } });

    expect(error.status).toBe(400);
    expect(error.campos.email).toBe('Inválido.');
  });

  test('sin respuesta es un error de red con status 0', () => {
    const error = normalizarError({ code: 'ERR_NETWORK', message: 'Network Error' });

    expect(error.status).toBe(0);
    expect(error.sinRespuesta).toBe(true);
    expect(error.tiempoAgotado).toBe(false);
    expect(error.mensaje).toBe('No pudimos conectar con el servidor. Revisá tu conexión e intentá nuevamente.');
  });

  test.each(['ECONNABORTED', 'ETIMEDOUT'])('%s es un tiempo agotado', (code) => {
    const error = normalizarError({ code });

    expect(error.tiempoAgotado).toBe(true);
    expect(error.mensaje).toBe('El servidor tardó demasiado en responder. Intentá nuevamente.');
  });

  test('un ErrorApi ya normalizado no se vuelve a envolver', () => {
    const original = normalizarRespuesta(409, { detail: 'Choque.' });

    expect(normalizarError(original)).toBe(original);
  });

  test('un valor inesperado también da un error de red', () => {
    expect(normalizarError(undefined).status).toBe(0);
    expect(normalizarError(new Error('falló')).status).toBe(0);
  });
});
