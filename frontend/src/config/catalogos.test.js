import { describe, expect, test } from 'vitest';
import {
  describir,
  describirModulo,
  ESTADO_REGISTRO,
  FILTRO_ESTADO_REGISTRO,
  opcionesDe,
  REGISTRO_ACTIVO,
  REGISTRO_BAJA,
  RUTAS_PANEL,
  TIPO_EVENTO_AUDITORIA,
} from './catalogos.js';

describe('tipos de evento de auditoría', () => {
  test('el evento 17 es el cambio de catálogo', () => {
    expect(describir(TIPO_EVENTO_AUDITORIA, 17)).toEqual({ etiqueta: 'Cambio de catálogo', badge: 'badge-aviso' });
  });

  test('el filtro de la auditoría ofrece el evento 17 con su etiqueta', () => {
    const opciones = opcionesDe(TIPO_EVENTO_AUDITORIA);

    expect(opciones).toContainEqual({ valor: '17', etiqueta: 'Cambio de catálogo' });
    expect(opciones).toHaveLength(17);
  });

  test('cubre todos los códigos del 1 al 17 sin saltos', () => {
    expect(Object.keys(TIPO_EVENTO_AUDITORIA).map(Number)).toEqual(Array.from({ length: 17 }, (_, i) => i + 1));
  });
});

describe('estado de un registro con baja lógica', () => {
  test('distingue activo y de baja', () => {
    expect(describir(ESTADO_REGISTRO, REGISTRO_ACTIVO).etiqueta).toBe('Activo');
    expect(describir(ESTADO_REGISTRO, REGISTRO_BAJA).etiqueta).toBe('De baja');
  });
});

describe('describirModulo', () => {
  test('traduce los módulos conocidos y muestra el código de uno nuevo', () => {
    expect(describirModulo('agenda')).toBe('Agenda');
    expect(describirModulo('sistema')).toBe('Sistema');
    expect(describirModulo('facturacion')).toBe('facturacion');
  });
});

describe('filtro de estado de los catálogos del sistema', () => {
  test('ofrece activos (1) y de baja (0) con los códigos del backend', () => {
    expect(FILTRO_ESTADO_REGISTRO.map(({ valor }) => valor)).toEqual(['1', '0']);
  });
});

describe('rutas del panel a las que se salta desde un listado', () => {
  test('apuntan a la configuración y a las canchas de /panel', () => {
    expect(RUTAS_PANEL).toEqual({ configuracion: '/panel', canchas: '/panel/canchas' });
  });
});
