import { describe, expect, test } from 'vitest';
import { cuerpoCancha, validarCancha, valoresDeCancha, VALORES_CANCHA_INICIALES } from './canchaAdmin.js';

const guardada = {
  id: 9,
  complejo: 3,
  deporte: 2,
  nombre: 'Cancha 1',
  tipo_superficie: 1,
  cobertura: 2,
  iluminacion: 3,
  duracion_turno_min: 60,
  precio_base: '38000.00',
  estado: 1,
};

describe('valoresDeCancha', () => {
  test('convierte códigos y precio a texto del formulario', () => {
    expect(valoresDeCancha(guardada)).toEqual({
      nombre: 'Cancha 1',
      deporte: '2',
      tipo_superficie: '1',
      cobertura: '2',
      iluminacion: '3',
      duracion_turno_min: '60',
      precio_base: '38000',
      estado: '1',
    });
  });
});

describe('validarCancha', () => {
  const valores = valoresDeCancha(guardada);

  test('una cancha completa no tiene errores', () => {
    expect(validarCancha(valores)).toEqual({});
  });

  test('exige nombre, deporte y un precio con a lo sumo dos decimales', () => {
    expect(Object.keys(validarCancha({ ...VALORES_CANCHA_INICIALES })).sort()).toEqual(['deporte', 'nombre', 'precio_base']);
    expect(validarCancha({ ...valores, precio_base: '10.555' })).toHaveProperty('precio_base');
    expect(validarCancha({ ...valores, precio_base: '-1' })).toHaveProperty('precio_base');
    expect(validarCancha({ ...valores, precio_base: '1500.50' })).toEqual({});
  });
});

describe('cuerpoCancha', () => {
  test('el alta lleva el complejo y todos los campos con códigos numéricos', () => {
    const cuerpo = cuerpoCancha({ ...valoresDeCancha(guardada), nombre: ' Cancha 2 ' }, { complejoId: 3 });

    expect(cuerpo).toEqual({
      complejo: 3,
      nombre: 'Cancha 2',
      precio_base: '38000',
      deporte: 2,
      tipo_superficie: 1,
      cobertura: 2,
      iluminacion: 3,
      duracion_turno_min: 60,
      estado: 1,
    });
  });

  test('la edición sin cambios queda vacía', () => {
    expect(cuerpoCancha(valoresDeCancha(guardada), { complejoId: 3, original: guardada })).toEqual({});
  });

  test('la edición envía solo lo modificado', () => {
    const valores = { ...valoresDeCancha(guardada), duracion_turno_min: '90', precio_base: '40000.00', estado: '2' };

    expect(cuerpoCancha(valores, { complejoId: 3, original: guardada })).toEqual({
      duracion_turno_min: 90,
      precio_base: '40000.00',
      estado: 2,
    });
  });
});
