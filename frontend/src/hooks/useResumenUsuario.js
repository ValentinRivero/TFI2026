import { obtenerResumenUsuario } from '../services/usuarioService.js';
import useConsulta from './useConsulta.js';

/** Resumen de una cuenta para el recuadro emergente de la auditoría; se pide una sola vez por id (ver `usuarioService`). */
export default function useResumenUsuario(usuarioId) {
  return useConsulta((signal) => obtenerResumenUsuario(usuarioId, signal), [usuarioId]);
}
