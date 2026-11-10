import { jest } from '@jest/globals';
import mongoose from 'mongoose';

import { conectarDB } from '../config/db.js';

const CLAVE_FICTICIA = 'clave-secreta-123';
// La URI se arma por partes a propósito: escrita entera tiene la forma de una credencial real y los escáneres de
// secretos (GitHub, por ejemplo) la reportan. El dominio `.invalid` está reservado para ejemplos.
const URI = `mongodb+srv://talibre:${CLAVE_FICTICIA}@cluster0.ejemplo.invalid/talibre`;

let conectar;
let consola;

beforeEach(() => {
  conectar = jest.spyOn(mongoose, 'connect').mockResolvedValue(mongoose);
  consola = {
    log: jest.spyOn(console, 'log').mockImplementation(() => {}),
    error: jest.spyOn(console, 'error').mockImplementation(() => {}),
  };
});

afterEach(() => {
  jest.restoreAllMocks();
  delete process.env.MONGO_URI;
});

const todoLoRegistrado = () => [...consola.log.mock.calls, ...consola.error.mock.calls].flat().map(String).join(' ');

describe('conectarDB', () => {
  test('se conecta con MONGO_URI y un tiempo máximo para encontrar el servidor', async () => {
    process.env.MONGO_URI = URI;

    await conectarDB();

    expect(conectar).toHaveBeenCalledWith(URI, expect.objectContaining({ serverSelectionTimeoutMS: expect.any(Number) }));
  });

  test('sin MONGO_URI falla con un mensaje claro y no intenta conectar', async () => {
    await expect(conectarDB()).rejects.toThrow('MONGO_URI no está configurada.');
    expect(conectar).not.toHaveBeenCalled();
  });

  test('si Atlas no responde propaga el error para que el servidor no arranque a medias', async () => {
    process.env.MONGO_URI = URI;
    conectar.mockRejectedValue(new Error(`Server selection timed out connecting to ${URI}`));

    await expect(conectarDB()).rejects.toThrow('Server selection timed out');
  });

  test('nunca registra la contraseña de la URI, ni al conectar ni al fallar', async () => {
    process.env.MONGO_URI = URI;
    await conectarDB();
    conectar.mockRejectedValue(new Error(`bad auth for ${URI}`));
    await conectarDB().catch(() => {});

    expect(todoLoRegistrado()).not.toContain(CLAVE_FICTICIA);
    expect(todoLoRegistrado()).toContain('MongoDB conectado');
  });

  test('una caída posterior de la conexión se registra sin exponer credenciales', async () => {
    process.env.MONGO_URI = URI;
    await conectarDB();

    mongoose.connection.emit('error', new Error(`connection reset for ${URI}`));
    mongoose.connection.emit('disconnected');

    expect(todoLoRegistrado()).toContain('MongoDB desconectado.');
    expect(todoLoRegistrado()).toContain('//***@cluster0');
    expect(todoLoRegistrado()).not.toContain(CLAVE_FICTICIA);
  });

  test('conectar varias veces no duplica los avisos de desconexión', async () => {
    process.env.MONGO_URI = URI;
    await conectarDB();
    await conectarDB();

    mongoose.connection.emit('disconnected');

    expect(consola.error.mock.calls.filter(([texto]) => texto === 'MongoDB desconectado.')).toHaveLength(1);
  });

  test('las consultas descartan operadores enviados como valores (inyección NoSQL)', () => {
    expect(mongoose.get('sanitizeFilter')).toBe(true);
  });
});
