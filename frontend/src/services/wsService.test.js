import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('./authService.js', () => ({ obtenerEstado: () => ({ access: null }) }));

const { conectarDisponibilidad } = await import('./wsService.js');

class SocketFalso {
  static CONNECTING = 0;
  static OPEN = 1;
  static instancias = [];

  constructor(url) {
    this.url = url;
    this.readyState = SocketFalso.CONNECTING;
    this.cerrado = false;
    SocketFalso.instancias.push(this);
  }

  close() {
    this.cerrado = true;
  }

  abrir() {
    this.readyState = SocketFalso.OPEN;
    this.onopen?.();
  }

  recibir(datos) {
    this.onmessage?.({ data: datos });
  }

  cortar() {
    this.onclose?.();
  }
}

describe('conectarDisponibilidad', () => {
  beforeEach(() => {
    SocketFalso.instancias = [];
    vi.stubGlobal('WebSocket', SocketFalso);
    vi.useFakeTimers();
    vi.spyOn(Math, 'random').mockReturnValue(0.5);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test('abre un único socket por complejo y no reintenta mientras la conexión sigue viva', () => {
    const conexion = conectarDisponibilidad({ complejoId: 7, alEvento: vi.fn() });
    SocketFalso.instancias[0].abrir();

    vi.advanceTimersByTime(10 * 60 * 1000);

    expect(SocketFalso.instancias).toHaveLength(1);
    expect(SocketFalso.instancias[0].url).toContain('/ws/complejos/7/disponibilidad/');
    conexion.cerrar();
  });

  test('entrega los eventos JSON y descarta los mensajes mal formados', () => {
    const alEvento = vi.fn();
    conectarDisponibilidad({ complejoId: 1, alEvento });
    const socket = SocketFalso.instancias[0];
    socket.abrir();

    socket.recibir('no es json');
    socket.recibir(JSON.stringify({ event: 'grilla_actualizada' }));

    expect(alEvento).toHaveBeenCalledTimes(1);
    expect(alEvento).toHaveBeenCalledWith({ event: 'grilla_actualizada' });
  });

  test('tras un corte reconecta en silencio con espera creciente e informa que fue una reconexión', () => {
    const alConectar = vi.fn();
    conectarDisponibilidad({ complejoId: 1, alEvento: vi.fn(), alConectar });
    SocketFalso.instancias[0].abrir();
    expect(alConectar).toHaveBeenLastCalledWith(false);

    SocketFalso.instancias[0].cortar();
    vi.advanceTimersByTime(999);
    expect(SocketFalso.instancias).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(SocketFalso.instancias).toHaveLength(2);

    SocketFalso.instancias[1].cortar();
    vi.advanceTimersByTime(1999);
    expect(SocketFalso.instancias).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(SocketFalso.instancias).toHaveLength(3);

    SocketFalso.instancias[2].abrir();
    expect(alConectar).toHaveBeenLastCalledWith(true);
  });

  test('una conexión lograda reinicia la espera', () => {
    conectarDisponibilidad({ complejoId: 1, alEvento: vi.fn() });
    SocketFalso.instancias[0].cortar();
    vi.advanceTimersByTime(1000);
    SocketFalso.instancias[1].cortar();
    vi.advanceTimersByTime(2000);
    SocketFalso.instancias[2].abrir();

    SocketFalso.instancias[2].cortar();
    vi.advanceTimersByTime(1000);

    expect(SocketFalso.instancias).toHaveLength(4);
  });

  test('cerrar detiene los reintentos pendientes', () => {
    const conexion = conectarDisponibilidad({ complejoId: 1, alEvento: vi.fn() });
    SocketFalso.instancias[0].abrir();
    SocketFalso.instancias[0].cortar();

    conexion.cerrar();
    vi.advanceTimersByTime(60_000);

    expect(SocketFalso.instancias).toHaveLength(1);
  });

  test('cerrar una conexión abierta la cierra sin disparar reconexión', () => {
    const conexion = conectarDisponibilidad({ complejoId: 1, alEvento: vi.fn() });
    const socket = SocketFalso.instancias[0];
    socket.abrir();

    conexion.cerrar();

    expect(socket.cerrado).toBe(true);
    expect(socket.onclose).toBeNull();
    vi.advanceTimersByTime(60_000);
    expect(SocketFalso.instancias).toHaveLength(1);
  });

  test('cerrar mientras conecta espera a que abra para cerrar y evita el error del navegador', () => {
    const conexion = conectarDisponibilidad({ complejoId: 1, alEvento: vi.fn() });
    const socket = SocketFalso.instancias[0];

    conexion.cerrar();
    expect(socket.cerrado).toBe(false);

    socket.abrir();
    expect(socket.cerrado).toBe(true);
    vi.advanceTimersByTime(60_000);
    expect(SocketFalso.instancias).toHaveLength(1);
  });
});
