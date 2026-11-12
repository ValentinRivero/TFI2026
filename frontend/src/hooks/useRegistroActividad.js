import { useEffect, useRef } from 'react';
import { EVENTO_ACTIVIDAD } from '../config/catalogos.js';
import { registrarActividad } from '../services/actividadService.js';

/**
 * Informa a `backend-node`, en segundo plano, la visita al complejo (una vez por pantalla, cuando ya cargó) y cada
 * fecha de la grilla que llega (no las recargas en vivo de la misma fecha, que no son una consulta nueva).
 */
export default function useRegistroActividad({ complejoId, complejoCargado, fechaGrilla }) {
  const visitaRegistrada = useRef(false);
  const fechaRegistrada = useRef(null);

  useEffect(() => {
    if (!complejoCargado || visitaRegistrada.current) return;
    visitaRegistrada.current = true;
    registrarActividad(EVENTO_ACTIVIDAD.COMPLEJO_VISTO, complejoId);
  }, [complejoCargado, complejoId]);

  useEffect(() => {
    if (!fechaGrilla || fechaRegistrada.current === fechaGrilla) return;
    fechaRegistrada.current = fechaGrilla;
    registrarActividad(EVENTO_ACTIVIDAD.GRILLA_CONSULTADA, complejoId, { fecha: fechaGrilla });
  }, [fechaGrilla, complejoId]);
}
