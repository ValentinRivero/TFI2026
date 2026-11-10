import { jest } from '@jest/globals';
import mongoose from 'mongoose';

import Evento, { TIPOS_EVENTO } from '../models/Evento.js';
import Notificacion, {
  CATEGORIAS_NOTIFICACION,
  ESTADOS_NOTIFICACION,
  PRIORIDADES_NOTIFICACION,
} from '../models/Notificacion.js';

const valida = (cambios = {}) => new Notificacion({
  complejo_id: 4,
  categoria: CATEGORIAS_NOTIFICACION.RESERVAS,
  mensaje: 'Nueva reserva para el martes a las 20:00 en Cancha 2.',
  ...cambios,
});

const erroresDe = (documento) => Object.keys(documento.validateSync()?.errors ?? {});

describe('Modelo Notificacion', () => {
  test('una notificación mínima es válida, normal y nace sin leer', () => {
    const notificacion = valida();

    expect(notificacion.validateSync()).toBeUndefined();
    expect(notificacion.prioridad).toBe(PRIORIDADES_NOTIFICACION.NORMAL);
    expect(notificacion.estado).toBe(ESTADOS_NOTIFICACION.NO_LEIDA);
    expect(notificacion.evento).toBeNull();
    expect(notificacion.usuario_id).toBeNull();
  });

  test('categorías, prioridades y estados coinciden con PROJECT.md', () => {
    expect(CATEGORIAS_NOTIFICACION).toEqual({ RESERVAS: 1, CUENTAS: 2, OPERATORIA: 3, SISTEMA: 4 });
    expect(PRIORIDADES_NOTIFICACION).toEqual({ NORMAL: 1, URGENTE: 2 });
    expect(ESTADOS_NOTIFICACION).toEqual({ BAJA: 0, NO_LEIDA: 1, LEIDA: 2 });
  });

  describe('destinatario', () => {
    test('sin complejo ni usuario es inválida', () => {
      const errores = erroresDe(valida({ complejo_id: null }));

      expect(errores).toContain('complejo_id');
    });

    test('la regla también se aplica en la validación que usa save()', async () => {
      await expect(valida({ complejo_id: null }).validate()).rejects.toThrow('destinatario');
    });

    test('puede ir solo a un usuario', () => {
      expect(valida({ complejo_id: null, usuario_id: 12 }).validateSync()).toBeUndefined();
    });

    test('puede ir a un usuario dentro de un complejo', () => {
      expect(valida({ usuario_id: 12 }).validateSync()).toBeUndefined();
    });

    test.each([0, -2, 1.5])('rechaza el destinatario %p', (id) => {
      expect(erroresDe(valida({ complejo_id: id }))).toContain('complejo_id');
      expect(erroresDe(valida({ usuario_id: id }))).toContain('usuario_id');
    });
  });

  test.each([undefined, 0, 5, 'RESERVAS'])('rechaza la categoría %p', (categoria) => {
    expect(erroresDe(valida({ categoria }))).toContain('categoria');
  });

  test.each([0, 3])('rechaza la prioridad %p', (prioridad) => {
    expect(erroresDe(valida({ prioridad }))).toContain('prioridad');
  });

  test.each([-1, 3])('rechaza el estado %p', (estado) => {
    expect(erroresDe(valida({ estado }))).toContain('estado');
  });

  describe('mensaje', () => {
    test('es obligatorio y no puede quedar vacío', () => {
      expect(erroresDe(valida({ mensaje: undefined }))).toContain('mensaje');
      expect(erroresDe(valida({ mensaje: '   ' }))).toContain('mensaje');
    });

    test('se guarda sin espacios sobrantes', () => {
      expect(valida({ mensaje: '  Turno cancelado.  ' }).mensaje).toBe('Turno cancelado.');
    });

    test('tiene un largo máximo de 280 caracteres', () => {
      expect(valida({ mensaje: 'a'.repeat(280) }).validateSync()).toBeUndefined();
      expect(erroresDe(valida({ mensaje: 'a'.repeat(281) }))).toContain('mensaje');
    });

    test.each([
      'Reserva de juan.perez@gmail.com confirmada.',
      'Escribir a CONTACTO@COMPLEJO.COM.AR para dudas.',
    ])('rechaza un mensaje con un email (dato personal): %s', (mensaje) => {
      expect(erroresDe(valida({ mensaje }))).toContain('mensaje');
    });

    test('admite fechas, horas y números de cancha, que no son datos personales', () => {
      expect(valida({ mensaje: 'Turno del 2026-11-24 a las 20:00 en Cancha 3 cancelado.' }).validateSync()).toBeUndefined();
    });
  });

  test('rechaza una referencia a evento que no es un ObjectId', () => {
    expect(erroresDe(valida({ evento: 'no-es-un-id' }))).toContain('evento');
  });

  test('la referencia apunta al modelo Evento', () => {
    expect(Notificacion.schema.path('evento').options.ref).toBe('Evento');
  });

  test('con el evento resuelto lo serializa anidado y con el mismo formato', () => {
    const evento = new Evento({ tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA, complejo_id: 4 });

    const json = valida({ evento }).toJSON();

    expect(json.evento).toEqual(expect.objectContaining({ id: evento.id, tipo_evento: TIPOS_EVENTO.RESERVA_REALIZADA }));
    expect(json.evento).not.toHaveProperty('_id');
    expect(json).not.toHaveProperty('_id');
    expect(json).not.toHaveProperty('__v');
  });

  test('sin resolver, el evento se serializa como su id', () => {
    const id = new mongoose.Types.ObjectId();

    expect(valida({ evento: id }).toJSON().evento).toEqual(id);
  });

  test('darDeBaja deja la notificación en baja lógica', async () => {
    const notificacion = valida();
    jest.spyOn(notificacion, 'save').mockResolvedValue(notificacion);

    await notificacion.darDeBaja();

    expect(notificacion.estado).toBe(ESTADOS_NOTIFICACION.BAJA);
  });

  test.each(['deleteOne', 'deleteMany', 'findOneAndDelete'])('%s está bloqueado', async (metodo) => {
    await expect(Notificacion[metodo]({ complejo_id: 4 })).rejects.toThrow('baja lógica');
  });

  test('tiene índices para la bandeja de un complejo y la de un usuario', () => {
    const indices = Notificacion.schema.indexes().map(([campos]) => campos);

    expect(indices).toContainEqual({ complejo_id: 1, estado: 1, fecha_creacion: -1 });
    expect(indices).toContainEqual({ usuario_id: 1, estado: 1, fecha_creacion: -1 });
  });
});

describe('Notificacion.bandeja', () => {
  const VIGENTES = { $in: [ESTADOS_NOTIFICACION.NO_LEIDA, ESTADOS_NOTIFICACION.LEIDA] };

  test('la del complejo trae sus avisos generales, sin los dirigidos a un usuario puntual', () => {
    expect(Notificacion.bandeja({ complejo_id: 4 }).getFilter()).toEqual({
      complejo_id: 4, usuario_id: null, estado: VIGENTES,
    });
  });

  test('la de un usuario trae todas las suyas, de cualquier complejo', () => {
    expect(Notificacion.bandeja({ usuario_id: 12 }).getFilter()).toEqual({ usuario_id: 12, estado: VIGENTES });
  });

  test('cuenta con el mismo filtro que lista', () => {
    expect(Notificacion.filtroDeBandeja({ complejo_id: 4 })).toEqual(Notificacion.bandeja({ complejo_id: 4 }).getFilter());
  });

  test('ordena de la más reciente a la más antigua', () => {
    expect(Notificacion.bandeja({ usuario_id: 12 }).getOptions().sort).toEqual({ fecha_creacion: -1 });
  });

  test('resuelve el evento con populate, solo si está activo y sin su metadata ni el usuario', () => {
    const { evento } = Notificacion.bandeja({ complejo_id: 4 })._mongooseOptions.populate;

    expect(evento.match).toEqual({ estado: 1 });
    expect(evento.select).toBe('tipo_evento complejo_id fecha_creacion');
  });

  test('sin destinatario no arma una consulta que traería las notificaciones de todos', () => {
    expect(() => Notificacion.bandeja({})).toThrow('destinatario');
  });
});
