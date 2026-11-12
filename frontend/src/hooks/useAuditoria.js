import { listarTodosLosContratos } from '../services/contratoService.js';
import { listarAuditoria } from '../services/auditoriaService.js';
import { FILTROS_AUDITORIA_INICIALES, validarFiltrosAuditoria } from '../utils/sistema.js';
import useConsulta from './useConsulta.js';
import useFiltrosAplicables from './useFiltrosAplicables.js';
import useListaPaginada from './useListaPaginada.js';

/**
 * Registro de auditoría (superadmin): lista paginada, del evento más reciente al más antiguo, filtrable por tipo,
 * usuario, complejo, IP de origen y rango de fechas. Los filtros se aplican con el botón "Buscar".
 */
export default function useAuditoria() {
  const filtros = useFiltrosAplicables(FILTROS_AUDITORIA_INICIALES, validarFiltrosAuditoria);
  const lista = useListaPaginada(
    (pagina, signal) => listarAuditoria(filtros.aplicados, pagina, signal),
    [filtros.aplicados],
  );
  const complejos = useConsulta((signal) => listarTodosLosContratos(signal), []);

  return { lista, filtros, complejos: complejos.datos ?? [] };
}
