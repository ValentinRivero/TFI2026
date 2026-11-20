import { describe, expect, test } from 'vitest';
import {
  describir,
  describirModulo,
  ESTADO_REGISTRO,
  opcionesDe,
  REGISTRO_ACTIVO,
  REGISTRO_BAJA,
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
