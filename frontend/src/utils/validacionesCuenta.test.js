import { describe, expect, test } from 'vitest';
import { PARAMETROS } from '../config/parametros.js';
import {
  validarEmail, validarLogin, validarNombre, validarPassword, validarRegistro, validarTelefono,
} from './validacionesCuenta.js';

const { limitesCampos, cuenta } = PARAMETROS;

describe('validarNombre', () => {
  test.each([
    'María José Pérez', "Nicolás O'Brien", 'Ana-Lucía Gómez', 'Juan Pérez Jr.', 'Ñandú Ríos', 'Zoë Müller', '  Li   Wei ',
  ])('acepta %s', (nombre) => {
    expect(validarNombre(nombre)).toBeNull();
  });

  test('acepta un acento compuesto (letra más marca)', () => {
    expect(validarNombre('María José')).toBeNull();
  });

  test.each([
    ['con números', 'Fabricio 2'],
    ['con un emoji', 'Fabri\u{1F4A5}cio'],
    ['con una sola letra', 'A'],
    ['que empieza con un símbolo', '-Fabricio'],
    ['con guion bajo', 'Fabricio_Medina'],
    ['con &', 'Pérez & Hijos'],
    ['con arroba', 'fabricio@medina'],
    ['con paréntesis', 'Fabricio (Fabri)'],
  ])('rechaza un nombre %s', (_motivo, nombre) => {
    expect(validarNombre(nombre)).toContain('letras');
  });

  test('vacío o de solo espacios pide completar el campo', () => {
    expect(validarNombre('')).toBe('Completá este campo.');
    expect(validarNombre('   ')).toBe('Completá este campo.');
  });

  test('el largo máximo es el de la base', () => {
    expect(validarNombre('a'.repeat(limitesCampos.nombre))).toBeNull();
    expect(validarNombre('a'.repeat(limitesCampos.nombre + 1))).not.toBeNull();
  });
});

describe('validarEmail', () => {
  test.each(['a@b.co', 'fabricio.medina+reservas@talibre.test', 'FABRICIO@Talibre.Test', "o'brien@talibre.test"])(
    'acepta %s',
    (email) => {
      expect(validarEmail(email)).toBeNull();
    },
  );

  test.each([
    ['sin dominio completo', 'a@b'],
    ['demasiado corto', 'a@b.c'],
    ['sin arroba', 'fabricio.talibre.test'],
    ['sin usuario', '@talibre.test'],
    ['con espacios', 'fabricio medina@talibre.test'],
    ['con un emoji', 'fabricio\u{1F600}@talibre.test'],
    ['con puntos seguidos', 'fabricio..medina@talibre.test'],
    ['con punto al inicio', '.fabricio@talibre.test'],
    ['con dominio de puntos seguidos', 'fabricio@talibre..test'],
  ])('rechaza un correo %s', (_motivo, email) => {
    expect(validarEmail(email)).toContain('correo');
  });

  test('el largo máximo es el de la base', () => {
    const sufijo = '@talibre.test';
    expect(validarEmail('a'.repeat(limitesCampos.email - sufijo.length) + sufijo)).toBeNull();
    expect(validarEmail('a'.repeat(limitesCampos.email - sufijo.length + 1) + sufijo)).not.toBeNull();
  });

  test('el mínimo es el del espejo de Django', () => {
    expect(cuenta.emailLargoMinimo).toBe(6);
    expect(validarEmail('')).toBe('Completá este campo.');
  });
});

describe('validarTelefono', () => {
  test.each(['', '   ', '3777 000206', '+54 (3777) 00-0206'])('acepta %j', (telefono) => {
    expect(validarTelefono(telefono)).toBeNull();
  });

  test.each(['12345', 'abcdefgh', '3777 00020\u{1F600}', '37770002+06', '3777 000206'.padEnd(limitesCampos.telefono + 1, '1')])(
    'rechaza %j',
    (telefono) => {
      expect(validarTelefono(telefono)).toContain('teléfono');
    },
  );
});

describe('validarPassword', () => {
  test('acepta letras, números y todos los símbolos permitidos', () => {
    expect(validarPassword(`Pelota${cuenta.passwordSimbolos}9`)).toBeNull();
  });

  test.each([
    ['espacios', 'Pelota Arco 2026'],
    ['ñ', 'Contraseña2026'],
    ['tildes', 'Clavé-Segura1'],
    ['un emoji', 'ClaveSegura\u{1F600}'],
    ['barra vertical', 'Pelota|Arco2026'],
    ['comillas', 'Pelota"Arco2026'],
    ['una tabulación', 'Pelota\tArco2026'],
  ])('rechaza una contraseña con %s e indica los símbolos permitidos', (_motivo, password) => {
    const mensaje = validarPassword(password);
    expect(mensaje).toContain(cuenta.passwordSimbolos);
    expect(mensaje).toContain('sin espacios');
  });

  test('exige el largo mínimo y respeta el máximo', () => {
    expect(validarPassword('Ab1!')).toContain('entre 8 y 128');
    expect(validarPassword('Ab1!'.repeat(33))).toContain('entre 8 y 128');
    expect(validarPassword('Ab1!'.repeat(32))).toBeNull();
  });

  test('vacía pide completar el campo', () => {
    expect(validarPassword('')).toBe('Completá este campo.');
  });
});

describe('validarRegistro', () => {
  const valido = { nombre_completo: 'Fabricio Medina', email: 'fabricio@talibre.test', telefono: '', password: 'Pelota&Arco#2026' };

  test('sin errores devuelve un objeto vacío', () => {
    expect(validarRegistro(valido)).toEqual({});
  });

  test('indica cada campo inválido por separado', () => {
    const errores = validarRegistro({ nombre_completo: 'Fab 1', email: 'x', telefono: 'abc', password: 'corta' });

    expect(Object.keys(errores).sort()).toEqual(['email', 'nombre_completo', 'password', 'telefono']);
  });
});

describe('validarLogin', () => {
  test('una contraseña anterior a las reglas de caracteres sigue siendo válida para ingresar', () => {
    expect(validarLogin({ email: 'jugador@talibre.test', password: 'Contraseña con espacios 1' })).toEqual({});
  });

  test('pide correo y contraseña vacíos y rechaza un correo mal formado', () => {
    expect(validarLogin({ email: '', password: '' })).toEqual({
      email: 'Completá este campo.',
      password: 'Completá este campo.',
    });
    expect(Object.keys(validarLogin({ email: 'jugador', password: 'x' }))).toEqual(['email']);
  });

  test('rechaza una contraseña de más del largo máximo', () => {
    const errores = validarLogin({ email: 'jugador@talibre.test', password: 'a'.repeat(limitesCampos.password + 1) });

    expect(Object.keys(errores)).toEqual(['password']);
  });
});
