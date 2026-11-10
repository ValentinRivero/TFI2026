import { jest } from '@jest/globals';

import Evento, { ESTADOS_EVENTO, TIPOS_EVENTO } from '../models/Evento.js';

const valido = (cambios = {}) => new Evento({ tipo_evento: TIPOS_EVENTO.COMPLEJO_VISTO, complejo_id: 4, ...cambios });

const erroresDe = (documento) => Object.keys(documento.validateSync()?.errors ?? {});

describe('Modelo Evento', () => {
  test('un evento mínimo es válido y nace activo, sin usuario y con metadata vacía', () => {
    const evento = valido();

    expect(evento.validateSync()).toBeUndefined();
    expect(evento.estado).toBe(ESTADOS_EVENTO.ACTIVO);
    expect(evento.usuario_id).toBeNull();
    expect(evento.metadata).toEqual({});
  });

  test('los tipos y estados coinciden con PROJECT.md', () => {
    expect(TIPOS_EVENTO).toEqual({ COMPLEJO_VISTO: 1, GRILLA_CONSULTADA: 2, RESERVA_REALIZADA: 3 });
    expect(ESTADOS_EVENTO).toEqual({ BAJA: 0, ACTIVO: 1 });
  });

  test.each([0, 4, 'VISITA', null])('rechaza el tipo de evento %p', (tipo) => {
    expect(erroresDe(valido({ tipo_evento: tipo }))).toContain('tipo_evento');
  });

  test.each([undefined, 0, -3, 2.5, 'abc'])('rechaza complejo_id %p', (complejo) => {
    expect(erroresDe(valido({ complejo_id: complejo }))).toContain('complejo_id');
  });

  test.each([0, -1, 1.5])('rechaza usuario_id %p', (usuario) => {
    expect(erroresDe(valido({ usuario_id: usuario }))).toContain('usuario_id');
  });

  test('acepta el usuario cuando el evento viene de una sesión', () => {
    expect(valido({ usuario_id: 12 }).validateSync()).toBeUndefined();
  });

  test.each([2, -1])('rechaza el estado %p', (estado) => {
    expect(erroresDe(valido({ estado }))).toContain('estado');
  });

  test('acepta metadata con datos simples, anidados y listas', () => {
    const metadata = { cancha_id: 3, origen: { pagina: 'mapa' }, filtros: ['padel', { techada: true }] };

    expect(valido({ metadata }).validateSync()).toBeUndefined();
  });

  test.each([
    ['una lista', ['a', 'b']],
    ['un texto', 'hola'],
    ['claves con operadores de MongoDB', { $where: 'sleep(1000)' }],
    ['operadores anidados', { filtro: { $gt: '' } }],
    ['operadores dentro de una lista', { canchas: [{ id: 1 }, { $ne: null }] }],
    ['claves con punto', { 'a.b': 1 }],
    ['más de 2 KB', { relleno: 'x'.repeat(2100) }],
  ])('rechaza metadata con %s', (_caso, metadata) => {
    expect(erroresDe(valido({ metadata }))).toContain('metadata');
  });

  test('descarta campos que no están en el esquema', () => {
    expect(valido({ es_admin: true }).toObject()).not.toHaveProperty('es_admin');
  });

  test('registra fecha de creación y de modificación con los nombres de Django', () => {
    expect(Evento.schema.path('fecha_creacion')).toBeDefined();
    expect(Evento.schema.path('fecha_modificacion')).toBeDefined();
  });

  test('al serializarse expone id y oculta _id y __v', () => {
    const json = valido().toJSON();

    expect(json.id).toEqual(expect.any(String));
    expect(json).not.toHaveProperty('_id');
    expect(json).not.toHaveProperty('__v');
  });

  test('darDeBaja pasa el evento a baja lógica y lo guarda', async () => {
    const evento = valido();
    const guardar = jest.spyOn(evento, 'save').mockResolvedValue(evento);

    await evento.darDeBaja();

    expect(evento.estado).toBe(ESTADOS_EVENTO.BAJA);
    expect(guardar).toHaveBeenCalled();
  });

  test.each(['deleteOne', 'deleteMany', 'findOneAndDelete'])('%s está bloqueado: solo hay baja lógica', async (metodo) => {
    await expect(Evento[metodo]({ complejo_id: 4 })).rejects.toThrow('baja lógica');
  });

  test('findByIdAndDelete también está bloqueado', async () => {
    await expect(Evento.findByIdAndDelete('6650a1b2c3d4e5f6a7b8c9d0')).rejects.toThrow('baja lógica');
  });

  test('borrar un documento ya cargado también está bloqueado', async () => {
    await expect(valido().deleteOne()).rejects.toThrow('baja lógica');
  });

  test('tiene un índice para listar por complejo los más recientes primero', () => {
    const indices = Evento.schema.indexes().map(([campos]) => campos);

    expect(indices).toContainEqual({ complejo_id: 1, estado: 1, fecha_creacion: -1 });
  });
});
