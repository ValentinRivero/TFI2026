/**
 * Canal de disponibilidad en tiempo real de un complejo. Es de solo lectura: el servidor ignora lo que el cliente
 * envía y los eventos no llevan datos personales. Archivo, junto con `api.js`, que conoce la URL del WebSocket.
 *
 * Reconecta con espera exponencial y jitter. Un complejo sin contrato activo rechaza el handshake y el navegador solo
 * ve un corte genérico, así que quien lo usa decide cuándo dejar de reintentar llamando a `cerrar()`.
 */
import { ENTORNO } from '../config/parametros.js';
import { armarUrlDisponibilidad, calcularEspera } from '../utils/tiempoReal.js';
import { obtenerEstado } from './authService.js';

/**
 * @param {object} opciones
 * @param {number|string} opciones.complejoId
 * @param {(evento: object) => void} opciones.alEvento mensaje JSON recibido
 * @param {(reconectada: boolean) => void} [opciones.alConectar] la conexión quedó abierta; `reconectada` es
 *   verdadero si antes hubo un corte (la grilla pudo cambiar sin que llegara el aviso)
 * @param {() => void} [opciones.alDesconectar] se perdió la conexión y se reintentará
 * @returns {{ cerrar: () => void }}
 */
export const conectarDisponibilidad = ({ complejoId, alEvento, alConectar, alDesconectar }) => {
  let socket = null;
  let temporizador = null;
  let cerrado = false;
  let intentos = 0;
  let huboCorte = false;

  const abrir = () => {
    // El access se lee en cada intento: el de una conexión vieja pudo vencer o renovarse.
    const token = obtenerEstado().access;
    socket = new WebSocket(armarUrlDisponibilidad(ENTORNO.urlWs, complejoId, token));

    socket.onopen = () => {
      intentos = 0;
      alConectar?.(huboCorte);
      huboCorte = false;
    };

    socket.onmessage = (mensaje) => {
      let evento;
      try {
        evento = JSON.parse(mensaje.data);
      } catch {
        return;
      }
      alEvento(evento);
    };

    socket.onclose = () => {
      socket = null;
      if (cerrado) return;
      huboCorte = true;
      alDesconectar?.();
      temporizador = setTimeout(abrir, calcularEspera(intentos));
      intentos += 1;
    };
  };

  abrir();

  return {
    cerrar: () => {
      cerrado = true;
      clearTimeout(temporizador);
      if (socket) {
        socket.onclose = null;
        socket.onmessage = null;
        socket.onopen = null;
        socket.close();
        socket = null;
      }
    },
  };
};
