import AlertaReintento from '../components/AlertaReintento.jsx';
import Cargando from '../components/Cargando.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosReporte from '../components/FiltrosReporte.jsx';
import ResultadoReporte from '../components/ResultadoReporte.jsx';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useReporte from '../hooks/useReporte.js';
import { t } from '../i18n/index.js';

/**
 * Dashboard estadístico del complejo activo (dueño y superadmin): recaudación, reservas por estado, ocupación por
 * cancha, horarios más demandados y visitas al perfil, para un rango de fechas elegido.
 */
export default function Reportes() {
  const { complejo } = useContextoPanel();
  const reporte = useReporte(complejo.id);
  const { dashboard } = reporte;

  return (
    <div>
      <EncabezadoPantalla titulo={t('reportes.titulo')} descripcion={t('reportes.descripcion')} />
      <FiltrosReporte filtros={reporte.filtros} canchas={reporte.canchas} deportes={reporte.deportes} />

      {dashboard.cargando && <Cargando variante="seccion" />}
      {!dashboard.cargando && dashboard.error && (
        <AlertaReintento titulo={t('reportes.errorTitulo')} mensaje={dashboard.error.mensaje} onReintentar={dashboard.recargar} />
      )}
      {!dashboard.cargando && !dashboard.error && dashboard.datos && (
        <ResultadoReporte dashboard={dashboard.datos} visitas={reporte.visitas} />
      )}
    </div>
  );
}
