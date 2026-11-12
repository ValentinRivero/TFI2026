import { formatearHora, parsearFecha } from './formatos.js';

const ES_ID = /^[1-9]\d{0,9}$/;
const ES_HORA = /^\d{2}:\d{2}(:\d{2})?$/;

/**
 * Query string con el turno elegido, para volver a él después de iniciar sesión: la ruta de origen del login
 * conserva complejo (en el camino), fecha, cancha y horario, y `reservar` reabre la confirmación.
 */
export const aParametrosRetorno = ({ fecha, canchaId, horaInicio }) => new URLSearchParams({
  fecha,
  cancha: String(canchaId),
  hora: formatearHora(horaInicio),
  reservar: '1',
}).toString();

/**
 * Turno a retomar según la URL de la ficha, o `null` si no trae uno completo y válido. Un valor manipulado se
 * descarta en lugar de usarse: el servidor valida igual al reservar.
 */
export const leerRetorno = (parametros) => {
  const fecha = parametros.get('fecha');
  const cancha = parametros.get('cancha');
  const hora = parametros.get('hora');
  if (!parsearFecha(fecha) || !ES_ID.test(cancha ?? '') || !ES_HORA.test(hora ?? '')) return null;
  return {
    fecha,
    canchaId: Number(cancha),
    horaInicio: formatearHora(hora),
    reservar: parametros.get('reservar') === '1',
  };
};

/** Ruta a la que vuelve el login: la de origen con su query string, o `null` si no venía redirigido. */
export const rutaDeRetorno = (desde) => (desde?.pathname ? `${desde.pathname}${desde.search ?? ''}` : null);
