import { describe, expect, test } from 'vitest';
import { t } from '../i18n/index.js';
import {
  agruparPermisosPorModulo,
  alternarPermiso,
  cuerpoRolEdicion,
  cuerpoRolNuevo,
  esRolEditable,
  validarRol,
  VALORES_ROL_INICIALES,
  valoresDeRol,
} from './roles.js';

const PERMISOS = [
  { id: 1, codigo: 'ver_agenda', nombre: 'Ver la agenda', modulo: 'agenda' },
  { id: 2, codigo: 'gestionar_agenda', nombre: 'Gestionar la agenda', modulo: 'agenda' },
  { id: 3, codigo: 'ver_canchas', nombre: 'Ver las canchas', modulo: 'canchas' },
];

const ROL = {
  id: 7,
  nombre: 'Encargado de Turno',
  descripcion: 'Atiende el mostrador',
  es_base: false,
  permisos: [PERMISOS[0], PERMISOS[2]],
};

describe('validarRol', () => {
  const valido = { nombre: 'Encargado', descripcion: '', permisos: [] };

  test('un rol sin permisos ni descripción es válido', () => {
    expect(validarRol(valido)).toEqual({});
  });

  test('el nombre es obligatorio, de al menos 2 y como máximo 50 caracteres', () => {
    expect(validarRol({ ...valido, nombre: '  ' }).nombre).toBe(t('catalogoSistema.errorNombreVacio'));
    expect(validarRol({ ...valido, nombre: 'A' }).nombre).toBe(t('catalogoSistema.errorNombreCorto', { minimo: 2 }));
    expect(validarRol({ ...valido, nombre: 'a'.repeat(50) })).toEqual({});
    expect(validarRol({ ...valido, nombre: 'a'.repeat(51) }).nombre).toBe(t('catalogoSistema.errorNombreLargo', { maximo: 50 }));
  });

  test('la descripción admite hasta 150 caracteres', () => {
    expect(validarRol({ ...valido, descripcion: 'x'.repeat(150) })).toEqual({});
    expect(validarRol({ ...valido, descripcion: 'x'.repeat(151) }).descripcion).toBe(t('roles.errorDescripcion', { maximo: 150 }));
  });
});

describe('cuerpoRolNuevo', () => {
  test('normaliza el nombre y no envía una descripción vacía', () => {
    expect(cuerpoRolNuevo({ nombre: '  Encargado   de Turno ', descripcion: '  ', permisos: [1, 3] })).toEqual({
      nombre: 'Encargado de Turno',
      permisos: [1, 3],
    });
  });

  test('envía la descripción cuando la hay', () => {
    expect(cuerpoRolNuevo({ nombre: 'Cajero', descripcion: ' Cobra ', permisos: [] })).toEqual({
      nombre: 'Cajero',
      descripcion: 'Cobra',
      permisos: [],
    });
  });
});

describe('cuerpoRolEdicion', () => {
  test('sin cambios no hay nada para enviar', () => {
    expect(cuerpoRolEdicion(valoresDeRol(ROL), ROL)).toEqual({});
  });

  test('un cambio de capitalización o de espacios internos del nombre sí se envía', () => {
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), nombre: 'ENCARGADO DE TURNO' }, ROL)).toEqual({ nombre: 'ENCARGADO DE TURNO' });
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), nombre: ' Encargado de Turno ' }, ROL)).toEqual({});
  });

  test('envía solo los campos modificados', () => {
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), descripcion: 'Otra' }, ROL)).toEqual({ descripcion: 'Otra' });
  });

  test('los permisos se comparan como conjunto y se envía la lista completa', () => {
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), permisos: [3, 1] }, ROL)).toEqual({});
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), permisos: [1, 2, 3] }, ROL)).toEqual({ permisos: [1, 2, 3] });
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), permisos: [] }, ROL)).toEqual({ permisos: [] });
  });

  test('una descripción vacía en un rol que la tenía se envía para borrarla', () => {
    expect(cuerpoRolEdicion({ ...valoresDeRol(ROL), descripcion: '' }, ROL)).toEqual({ descripcion: '' });
  });
});

describe('valoresDeRol', () => {
  test('toma los ids de los permisos y una descripción ausente es un texto vacío', () => {
    expect(valoresDeRol(ROL)).toEqual({ nombre: 'Encargado de Turno', descripcion: 'Atiende el mostrador', permisos: [1, 3] });
    expect(valoresDeRol({ ...ROL, descripcion: null }).descripcion).toBe('');
  });
});

describe('alternarPermiso', () => {
  test('agrega un permiso que no estaba y quita el que ya estaba, sin mutar la lista', () => {
    const original = Object.freeze([1]);

    expect(alternarPermiso(original, 2)).toEqual([1, 2]);
    expect(alternarPermiso(original, 1)).toEqual([]);
  });

  test('el estado inicial de un rol nuevo no tiene permisos', () => {
    expect(VALORES_ROL_INICIALES.permisos).toEqual([]);
  });
});

describe('agruparPermisosPorModulo', () => {
  test('junta los permisos de cada módulo conservando el orden de llegada', () => {
    expect(agruparPermisosPorModulo(PERMISOS)).toEqual([
      { modulo: 'agenda', permisos: [PERMISOS[0], PERMISOS[1]] },
      { modulo: 'canchas', permisos: [PERMISOS[2]] },
    ]);
  });

  test('sin permisos no hay grupos', () => {
    expect(agruparPermisosPorModulo([])).toEqual([]);
  });
});

describe('esRolEditable', () => {
  test('un rol base es de solo lectura y uno personalizado se edita', () => {
    expect(esRolEditable({ es_base: true })).toBe(false);
    expect(esRolEditable({ es_base: false })).toBe(true);
  });
});

describe('textos de la pantalla de roles', () => {
  test.each([
    'titulo', 'descripcion', 'nuevo', 'rolBase', 'protegido', 'usosUno', 'usosVarios', 'verPermisos', 'darDeBaja',
    'reactivar', 'resumen', 'errorTitulo', 'vacioTitulo', 'vacioDescripcion', 'fichaTitulo', 'fichaBase', 'sinPermisos',
    'tituloAlta', 'tituloEdicion', 'campoNombre', 'ayudaNombre', 'campoDescripcion', 'errorDescripcion', 'permisos',
    'ayudaPermisos', 'permisoReservado', 'errorPermisos', 'bajaTitulo', 'bajaTexto', 'bajaTextoEnUso', 'avisoAlta',
    'avisoEdicion', 'avisoBaja', 'avisoReactivacion',
  ])('existe roles.%s', (clave) => {
    expect(t(`roles.${clave}`)).not.toBe(`roles.${clave}`);
  });
});
