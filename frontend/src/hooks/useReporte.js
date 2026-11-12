import { listarDeportes } from '../services/complejoService.js';
import { obtenerVisitas } from '../services/actividadService.js';
import { obtenerDashboard } from '../services/reporteService.js';
import { aFechaIso } from '../utils/formatos.js';
import { filtrosReporteIniciales, validarFiltrosReporte } from '../utils/reportes.js';
import useCanchasDelComplejo from './useCanchasDelComplejo.js';
import useConsulta from './useConsulta.js';
import useFiltrosAplicables from './useFiltrosAplicables.js';

/**
 * Dashboard del complejo activo en un rango de fechas. Las métricas de reservas vienen de Django; las visitas al
 * perfil, de `backend-node` en una consulta aparte: si Node no responde, solo esa tarjeta muestra el error.
 * El rango se aplica con el botón "Consultar", no en cada cambio de campo.
 */
export default function useReporte(complejoId) {
  const hoy = aFechaIso(new Date());
  const filtros = useFiltrosAplicables(filtrosReporteIniciales(hoy), validarFiltrosReporte);
  const { aplicados } = filtros;

  const canchas = useCanchasDelComplejo(complejoId);
  const deportes = useConsulta((signal) => listarDeportes(signal), []);

  const dashboard = useConsulta(
    (signal) => obtenerDashboard(complejoId, aplicados, signal),
    [complejoId, aplicados],
  );
  const visitas = useConsulta(
    (signal) => obtenerVisitas(complejoId, aplicados.fecha_desde, aplicados.fecha_hasta, signal),
    [complejoId, aplicados.fecha_desde, aplicados.fecha_hasta],
  );

  return {
    filtros,
    hoy,
    canchas,
    deportes: deportes.datos ?? [],
    dashboard,
    visitas,
    // Los filtros aplicados que describen lo que se está mostrando (el borrador puede ir por delante).
    aplicados,
  };
}
