import { obtenerGrilla } from '../services/complejoService.js';
import { parsearFecha } from '../utils/formatos.js';
import useConsulta from './useConsulta.js';
import useDisponibilidadEnVivo from './useDisponibilidadEnVivo.js';

/**
 * Bloques reales de una cancha en un día, de la misma grilla que ven los jugadores (`GET .../grilla/`), mantenidos al
 * día por el canal de disponibilidad: si alguien reserva o se carga una excepción mientras se completa el formulario,
 * el casillero cambia de estado. Sin cancha o con una fecha inválida o pasada no consulta (el backend la rechaza).
 *
 * Devuelve `{ listo, cargando, error, bloques }`. `bloques` solo trae los de la cancha y la fecha vigentes: mientras
 * llegan los de una elección nueva no se muestran los de la anterior.
 */
export default function useBloquesDeCancha({ complejoId, canchaId, fecha, hoy, habilitado }) {
  const clave = canchaId === '' || canchaId === null || canchaId === undefined ? '' : String(canchaId);
  const listo = Boolean(habilitado && clave && parsearFecha(fecha) && fecha >= hoy);

  const consulta = useConsulta(async (signal) => {
    if (!listo) return null;
    const grilla = await obtenerGrilla(complejoId, fecha, signal);
    const cancha = grilla.canchas.find((candidata) => String(candidata.id) === clave) ?? null;
    return { fecha, clave, cancha };
  }, [complejoId, listo, fecha, clave]);

  useDisponibilidadEnVivo({
    complejoId,
    habilitado: listo && consulta.error?.status !== 404,
    fecha,
    canchaIds: listo ? [Number(clave)] : null,
    alRecargar: consulta.recargar,
  });

  const vigente = consulta.datos && consulta.datos.fecha === fecha && consulta.datos.clave === clave ? consulta.datos : null;

  return {
    listo,
    cargando: listo && consulta.cargando && !vigente,
    error: listo ? consulta.error : null,
    bloques: vigente?.cancha?.bloques ?? [],
  };
}
