import { describe, expect, test } from 'vitest';
import {
  aParametrosAuditoria,
  aParametrosContratos,
  aParametrosUsuarios,
  cuerpoComplejoNuevo,
  cuerpoUsuario,
  esDireccionIp,
  idDeUsuarioEnRuta,
  FILTROS_AUDITORIA_INICIALES,
  FILTROS_CONTRATOS_INICIALES,
  FILTROS_USUARIOS_INICIALES,
  validarComplejoNuevo,
  validarFiltrosAuditoria,
  validarUsuario,
  valoresDeUsuario,
  VALORES_COMPLEJO_NUEVO_INICIALES,
} from './sistema.js';

describe('aParametrosContratos', () => {
  test('por defecto ordena por nombre y no envía filtros vacíos', () => {
    expect(aParametrosContratos(FILTROS_CONTRATOS_INICIALES, 1)).toEqual({ page: 1, ordering: 'nombre' });
  });

  test('traduce el estado y la búsqueda a los nombres de la API', () => {
    const filtros = { estado: '3', busqueda: ' timbo ', orden: '-fecha_creacion' };

    expect(aParametrosContratos(filtros, 2)).toEqual({
      page: 2, estado_contrato: '3', search: 'timbo', ordering: '-fecha_creacion',
    });
  });

  test('el estado Baja (0) es un filtro válido', () => {
    expect(aParametrosContratos({ ...FILTROS_CONTRATOS_INICIALES, estado: '0' }, 1)).toMatchObject({ estado_contrato: '0' });
  });
});

describe('validarComplejoNuevo y cuerpoComplejoNuevo', () => {
  const valido = {
    ...VALORES_COMPLEJO_NUEVO_INICIALES,
    propietario: '4',
    nombre: ' Complejo de muestra ',
    direccion: 'Calle de muestra 100',
    latitud: '-29.14',
    longitud: '-59.26',
  };

  test('el estado inicial usa el límite de cancelación por defecto del backend', () => {
    expect(VALORES_COMPLEJO_NUEVO_INICIALES.horas_limite_cancelacion).toBe('4');
  });

  test('un complejo completo no tiene errores', () => {
    expect(validarComplejoNuevo(valido)).toEqual({});
  });

  test('exige el propietario además de los datos del complejo', () => {
    const errores = validarComplejoNuevo(VALORES_COMPLEJO_NUEVO_INICIALES);

    expect(errores).toHaveProperty('propietario');
    expect(errores).toHaveProperty('nombre');
    expect(errores).toHaveProperty('latitud');
  });

  test('el cuerpo recorta los textos, convierte los números y omite los opcionales vacíos', () => {
    expect(cuerpoComplejoNuevo(valido)).toEqual({
      propietario: 4,
      nombre: 'Complejo de muestra',
      direccion: 'Calle de muestra 100',
      latitud: '-29.14',
      longitud: '-59.26',
      horas_limite_cancelacion: 4,
      estado_contrato: 1,
    });
  });

  test('incluye el teléfono y la información de seña cuando se completan', () => {
    const cuerpo = cuerpoComplejoNuevo({ ...valido, telefono_contacto: '3777 001234', info_sena: 'Alias de muestra', estado_contrato: '2' });

    expect(cuerpo).toMatchObject({ telefono_contacto: '3777 001234', info_sena: 'Alias de muestra', estado_contrato: 2 });
  });
});

describe('aParametrosUsuarios', () => {
  test('sin filtros pide solo la página', () => {
    expect(aParametrosUsuarios(FILTROS_USUARIOS_INICIALES, 1)).toEqual({ page: 1 });
  });

  test('el rol viaja por nombre y la búsqueda recortada', () => {
    expect(aParametrosUsuarios({ rol: 'DUENO_COMPLEJO', estado: '1', busqueda: ' ana ' }, 3)).toEqual({
      page: 3, rol: 'DUENO_COMPLEJO', estado: '1', search: 'ana',
    });
  });
});

describe('cuerpoUsuario', () => {
  const original = {
    nombre_completo: 'Cuenta de muestra',
    telefono: '3777 001234',
    rol: 'OPERADOR_COMPLEJO',
    complejo_operado: 4,
    estado: 1,
  };

  test('sin cambios el cuerpo queda vacío', () => {
    expect(cuerpoUsuario(valoresDeUsuario(original), original)).toEqual({});
  });

  test('envía solo lo que cambió', () => {
    const valores = { ...valoresDeUsuario(original), nombre_completo: ' Otro nombre ', estado: '2' };

    expect(cuerpoUsuario(valores, original)).toEqual({ nombre_completo: 'Otro nombre', estado: 2 });
  });

  test('quitar el complejo de un operador envía null', () => {
    const valores = { ...valoresDeUsuario(original), complejo_operado: '' };

    expect(cuerpoUsuario(valores, original)).toEqual({ complejo_operado: null });
  });

  test('con un rol que no es operador no envía el complejo operado', () => {
    const valores = { ...valoresDeUsuario(original), rol: 'JUGADOR', complejo_operado: '9' };

    expect(cuerpoUsuario(valores, original)).toEqual({ rol: 'JUGADOR' });
  });

  test('un usuario sin teléfono ni complejo se interpreta como texto vacío', () => {
    const valores = valoresDeUsuario({ ...original, telefono: null, complejo_operado: null });

    expect(valores).toMatchObject({ telefono: '', complejo_operado: '' });
  });
});

describe('validarUsuario', () => {
  test('el nombre es obligatorio', () => {
    expect(validarUsuario({ nombre_completo: '  ' })).toHaveProperty('nombre_completo');
    expect(validarUsuario({ nombre_completo: 'Cuenta de muestra' })).toEqual({});
  });
});

describe('esDireccionIp', () => {
  test('acepta IPv4 e IPv6 y rechaza el resto', () => {
    expect(esDireccionIp('192.168.0.10')).toBe(true);
    expect(esDireccionIp('::1')).toBe(true);
    expect(esDireccionIp('2001:db8::ff00:42:8329')).toBe(true);
    expect(esDireccionIp('256.1.1.1')).toBe(false);
    expect(esDireccionIp('192.168.0')).toBe(false);
    expect(esDireccionIp('hola')).toBe(false);
  });
});

describe('filtros de auditoría', () => {
  test('sin filtros no valida errores ni envía parámetros salvo la página', () => {
    expect(validarFiltrosAuditoria(FILTROS_AUDITORIA_INICIALES)).toEqual({});
    expect(aParametrosAuditoria(FILTROS_AUDITORIA_INICIALES, 1)).toEqual({ page: 1 });
  });

  test('valida el usuario, la IP y el orden del rango', () => {
    const errores = validarFiltrosAuditoria({
      ...FILTROS_AUDITORIA_INICIALES,
      usuario: 'abc',
      ip_origen: '999.1.1.1',
      fecha_desde: '2026-11-12',
      fecha_hasta: '2026-11-01',
    });

    expect(Object.keys(errores).sort()).toEqual(['fecha_hasta', 'ip_origen', 'usuario']);
  });

  test('traduce los filtros a los nombres de la API', () => {
    const filtros = {
      tipo_evento: '2', usuario: ' 7 ', complejo: '4', ip_origen: ' 10.0.0.1 ', fecha_desde: '2026-11-01', fecha_hasta: '2026-11-12',
    };

    expect(aParametrosAuditoria(filtros, 2)).toEqual({
      page: 2, tipo_evento: '2', usuario: '7', complejo: '4', ip_origen: '10.0.0.1', fecha_desde: '2026-11-01', fecha_hasta: '2026-11-12',
    });
  });
});

describe('idDeUsuarioEnRuta', () => {
  test('acepta un entero positivo', () => {
    expect(idDeUsuarioEnRuta('7')).toBe(7);
    expect(idDeUsuarioEnRuta('1204')).toBe(1204);
  });

  test('descarta lo ausente, cero, negativos, decimales y texto', () => {
    ['', null, undefined, '0', '-3', '2.5', 'abc', '7abc', '01'].forEach((valor) => {
      expect(idDeUsuarioEnRuta(valor)).toBeNull();
    });
  });
});
