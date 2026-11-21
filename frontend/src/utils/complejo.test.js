import { describe, expect, test } from 'vitest';
import {
  cuerpoConfiguracion,
  resolverComplejoActivo,
  serviciosModificados,
  validarConfiguracion,
  validarConfiguracionConSena,
  valoresDeComplejo,
} from './complejo.js';

const complejo = {
  id: 3,
  nombre: 'Complejo Los Aromos',
  direccion: 'Calle Ficticia 123',
  latitud: '-29.140000',
  longitud: '-59.260000',
  telefono_contacto: '3777 001234',
  horas_limite_cancelacion: 4,
  info_sena: '',
  porcentaje_sena: 0,
  alias_transferencia: '',
  titular_transferencia: '',
};

describe('resolverComplejoActivo', () => {
  const lista = [{ id: 1 }, { id: 2 }];

  test('devuelve el elegido si sigue en la lista', () => {
    expect(resolverComplejoActivo(lista, 2)).toEqual({ id: 2 });
  });

  test('sin elección o con un id que ya no está usa el primero', () => {
    expect(resolverComplejoActivo(lista, null)).toEqual({ id: 1 });
    expect(resolverComplejoActivo(lista, 99)).toEqual({ id: 1 });
  });

  test('con la lista vacía no hay complejo activo', () => {
    expect(resolverComplejoActivo([], 1)).toBeNull();
  });
});

describe('valoresDeComplejo', () => {
  test('todos los valores son texto y un campo ausente queda vacío', () => {
    const valores = valoresDeComplejo(complejo);

    expect(valores.horas_limite_cancelacion).toBe('4');
    expect(valores.info_sena).toBe('');
    expect(valoresDeComplejo({ ...complejo, telefono_contacto: null }).telefono_contacto).toBe('');
  });
});

describe('cuerpoConfiguracion', () => {
  test('sin cambios el cuerpo queda vacío', () => {
    expect(cuerpoConfiguracion(valoresDeComplejo(complejo), complejo)).toEqual({});
  });

  test('una coordenada equivalente escrita distinto no es un cambio', () => {
    const valores = { ...valoresDeComplejo(complejo), latitud: '-29.14' };

    expect(cuerpoConfiguracion(valores, complejo)).toEqual({});
  });

  test('solo viajan los campos modificados y las horas van como entero', () => {
    const valores = { ...valoresDeComplejo(complejo), nombre: ' Los Aromos II ', horas_limite_cancelacion: '6' };

    expect(cuerpoConfiguracion(valores, complejo)).toEqual({ nombre: 'Los Aromos II', horas_limite_cancelacion: 6 });
  });

  test('vaciar un campo opcional se envía como texto vacío', () => {
    const valores = { ...valoresDeComplejo(complejo), telefono_contacto: '' };

    expect(cuerpoConfiguracion(valores, complejo)).toEqual({ telefono_contacto: '' });
  });
});

describe('validarConfiguracion', () => {
  test('valores correctos no tienen errores', () => {
    expect(validarConfiguracion(valoresDeComplejo(complejo))).toEqual({});
  });

  test('marca obligatorios, coordenadas fuera de rango y horas inválidas', () => {
    const errores = validarConfiguracion({
      ...valoresDeComplejo(complejo),
      nombre: ' ',
      latitud: '95',
      longitud: 'abc',
      horas_limite_cancelacion: '169',
    });

    expect(Object.keys(errores).sort()).toEqual(['horas_limite_cancelacion', 'latitud', 'longitud', 'nombre']);
  });

  test('admite hasta 6 decimales en las coordenadas y rechaza más', () => {
    const base = valoresDeComplejo(complejo);

    expect(validarConfiguracion({ ...base, latitud: '-29.140123', longitud: '-59.260123' })).toEqual({});
    expect(validarConfiguracion({ ...base, latitud: '-29.1', longitud: '-59' })).toEqual({});

    const errores = validarConfiguracion({ ...base, latitud: '-29.1401234', longitud: ' -59.2601234 ' });
    expect(Object.keys(errores).sort()).toEqual(['latitud', 'longitud']);
    expect(errores.latitud).toContain('6');
  });

  test('un valor fuera de rango informa el rango aunque también tenga muchos decimales', () => {
    const errores = validarConfiguracion({ ...valoresDeComplejo(complejo), latitud: '95.1234567' });

    expect(errores.latitud).toContain('90');
  });

  test('las horas deben ser un entero no negativo', () => {
    expect(validarConfiguracion({ ...valoresDeComplejo(complejo), horas_limite_cancelacion: '-1' })).toHaveProperty('horas_limite_cancelacion');
    expect(validarConfiguracion({ ...valoresDeComplejo(complejo), horas_limite_cancelacion: '1.5' })).toHaveProperty('horas_limite_cancelacion');
    expect(validarConfiguracion({ ...valoresDeComplejo(complejo), horas_limite_cancelacion: '0' })).toEqual({});
  });
});

describe('serviciosModificados', () => {
  test('ignora el orden', () => {
    expect(serviciosModificados([1, 2], [2, 1])).toBe(false);
  });

  test('detecta altas y bajas', () => {
    expect(serviciosModificados([1, 2], [1])).toBe(true);
    expect(serviciosModificados([1], [1, 3])).toBe(true);
    expect(serviciosModificados([1, 2], [1, 3])).toBe(true);
  });
});

describe('seña y datos de transferencia', () => {
  const conSena = { ...complejo, porcentaje_sena: 30, alias_transferencia: 'YACARE.SENA', titular_transferencia: 'Yacaré Deportes' };

  test('los valores del formulario incluyen porcentaje, alias y titular como texto', () => {
    const valores = valoresDeComplejo(conSena);

    expect(valores).toMatchObject({ porcentaje_sena: '30', alias_transferencia: 'YACARE.SENA', titular_transferencia: 'Yacaré Deportes' });
    expect(valoresDeComplejo(complejo)).toMatchObject({ porcentaje_sena: '0', alias_transferencia: '', titular_transferencia: '' });
  });

  test('el porcentaje viaja como entero y el alias normalizado en mayúsculas', () => {
    const valores = { ...valoresDeComplejo(complejo), porcentaje_sena: '25', alias_transferencia: ' mi.alias-ok ' };

    expect(cuerpoConfiguracion(valores, complejo)).toEqual({ porcentaje_sena: 25, alias_transferencia: 'MI.ALIAS-OK' });
  });

  test('un alias que solo difiere en mayúsculas del guardado se envía normalizado', () => {
    const valores = { ...valoresDeComplejo(conSena), alias_transferencia: 'yacare.sena' };

    expect(cuerpoConfiguracion(valores, conSena)).toEqual({ alias_transferencia: 'YACARE.SENA' });
  });

  test('quitar la seña envía porcentaje 0 y el alias vacío', () => {
    const valores = { ...valoresDeComplejo(conSena), porcentaje_sena: '0', alias_transferencia: '' };

    expect(cuerpoConfiguracion(valores, conSena)).toEqual({ porcentaje_sena: 0, alias_transferencia: '' });
  });

  test('la validación del perfil no pide seña, pero la de configuración sí valida su alias', () => {
    const valores = { ...valoresDeComplejo(complejo), porcentaje_sena: '30', alias_transferencia: '' };

    expect(validarConfiguracion(valores)).toEqual({});
    expect(Object.keys(validarConfiguracionConSena(valores))).toEqual(['alias_transferencia']);
  });

  test('un complejo sin seña ni alias es válido', () => {
    expect(validarConfiguracionConSena(valoresDeComplejo(complejo))).toEqual({});
  });
});
