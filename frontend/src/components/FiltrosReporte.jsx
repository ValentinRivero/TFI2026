import Col from 'react-bootstrap/Col';
import { CRITERIO_REPORTE, opcionesDe } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import BarraFiltros from './BarraFiltros.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_CRITERIO = opcionesDe(CRITERIO_REPORTE);

/**
 * Filtros del dashboard: rango de fechas obligatorio, criterio de fecha, cancha y deporte. `filtros` es lo que devuelve
 * `useFiltrosAplicables` (borrador, errores, `cambiar`, `aplicar` y `limpiar`).
 */
export default function FiltrosReporte({ filtros, canchas, deportes }) {
  const { borrador, errores, cambiar } = filtros;

  return (
    <BarraFiltros
      etiqueta={t('reportes.filtros')}
      textoAplicar={t('reportes.consultar')}
      onAplicar={filtros.aplicar}
      onLimpiar={filtros.limpiar}
    >
      <Col sm={6} lg={3} xl={2}>
        <CampoFormulario
          id="reporte-desde"
          etiqueta={t('reportes.desde')}
          type="date"
          valor={borrador.fecha_desde}
          onCambiar={(valor) => cambiar('fecha_desde', valor)}
          error={errores.fecha_desde}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={2}>
        <CampoFormulario
          id="reporte-hasta"
          etiqueta={t('reportes.hasta')}
          type="date"
          valor={borrador.fecha_hasta}
          onCambiar={(valor) => cambiar('fecha_hasta', valor)}
          error={errores.fecha_hasta}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={2}>
        <CampoSelect
          id="reporte-criterio"
          etiqueta={t('reportes.criterio')}
          valor={borrador.criterio}
          onCambiar={(valor) => cambiar('criterio', valor)}
          opciones={OPCIONES_CRITERIO}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={2}>
        <CampoSelect
          id="reporte-cancha"
          etiqueta={t('reportes.cancha')}
          valor={borrador.cancha}
          onCambiar={(valor) => cambiar('cancha', valor)}
          placeholder={t('reportes.todasLasCanchas')}
          opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={2}>
        <CampoSelect
          id="reporte-deporte"
          etiqueta={t('reportes.deporte')}
          valor={borrador.deporte}
          onCambiar={(valor) => cambiar('deporte', valor)}
          placeholder={t('reportes.todosLosDeportes')}
          opciones={deportes.map((deporte) => ({ valor: String(deporte.id), etiqueta: deporte.nombre }))}
          className="mb-0"
        />
      </Col>
    </BarraFiltros>
  );
}
