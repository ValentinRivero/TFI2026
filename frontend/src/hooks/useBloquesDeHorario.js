import { listarHorarios } from '../services/canchaService.js';
import { bloquesDeHorarios } from '../utils/turnosFijos.js';
import useConsulta from './useConsulta.js';

/**
 * Bloques horarios válidos de una cancha en un día de la semana, a partir de sus horarios de apertura
 * (`GET /api/horarios/?cancha=`) y de la duración del turno de la cancha. `canchas` es la lista del complejo con
 * `duracion_turno_min` y `precio_base`. Sin cancha o sin día elegidos no hay bloques ni se consulta.
 *
 * Devuelve `{ listo, bloques, cargando, error, recargar }`; `listo` indica que ya se eligieron la cancha y el día.
 */
export default function useBloquesDeHorario({ canchaId, diaSemana, canchas }) {
  const hayCancha = canchaId !== '' && canchaId !== null && canchaId !== undefined;
  const hayDia = diaSemana !== '' && diaSemana !== null && diaSemana !== undefined;
  const rangos = useConsulta(
    (signal) => (hayCancha ? listarHorarios(canchaId, signal) : []),
    [hayCancha ? String(canchaId) : ''],
  );
  const cancha = canchas.find((candidata) => String(candidata.id) === String(canchaId));
  const listo = hayCancha && hayDia && Boolean(cancha);

  return {
    listo,
    bloques: listo ? bloquesDeHorarios(rangos.datos ?? [], diaSemana, cancha.duracion_turno_min, cancha.precio_base) : [],
    cargando: hayCancha && rangos.cargando,
    error: hayCancha ? rangos.error : null,
    recargar: rangos.recargar,
  };
}
