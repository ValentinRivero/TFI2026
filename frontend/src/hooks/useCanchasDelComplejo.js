import { listarTodasLasCanchas } from '../services/canchaService.js';
import useConsulta from './useConsulta.js';

/** Canchas vigentes del complejo para los selectores del panel (agenda, turnos fijos, reportes). */
export default function useCanchasDelComplejo(complejoId) {
  const consulta = useConsulta((signal) => listarTodasLasCanchas(complejoId, signal), [complejoId]);
  return consulta.datos ?? [];
}
