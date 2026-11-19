import Col from 'react-bootstrap/Col';
import { opcionesDe, TIPO_EVENTO_AUDITORIA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import BarraFiltros from './BarraFiltros.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_TIPO = opcionesDe(TIPO_EVENTO_AUDITORIA);

/**
 * Filtros del registro de auditoría: tipo de evento, usuario (por id), complejo, IP de origen y rango de fechas.
 * `filtros` es lo que devuelve `useFiltrosAplicables`; `complejos` es `[{ id, nombre }]`.
 */
export default function FiltrosAuditoria({ filtros, complejos }) {
  const { borrador, errores, cambiar } = filtros;

  return (
    <BarraFiltros etiqueta={t('auditoria.filtros')} onAplicar={filtros.aplicar} onLimpiar={filtros.limpiar}>
      <Col sm={6} lg={4} xl={3}>
        <CampoSelect
          id="auditoria-tipo"
          etiqueta={t('auditoria.tipoEvento')}
          valor={borrador.tipo_evento}
          onCambiar={(valor) => cambiar('tipo_evento', valor)}
          placeholder={t('auditoria.todosLosTipos')}
          opciones={OPCIONES_TIPO}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={4} xl={3}>
        <CampoSelect
          id="auditoria-complejo"
          etiqueta={t('auditoria.complejo')}
          valor={borrador.complejo}
          onCambiar={(valor) => cambiar('complejo', valor)}
          placeholder={t('auditoria.todosLosComplejos')}
          opciones={complejos.map((complejo) => ({ valor: String(complejo.id), etiqueta: complejo.nombre }))}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={4} xl={2}>
        <CampoFormulario
          id="auditoria-usuario"
          etiqueta={t('auditoria.usuario')}
          inputMode="numeric"
          valor={borrador.usuario}
          onCambiar={(valor) => cambiar('usuario', valor)}
          error={errores.usuario}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={4} xl={2}>
        <CampoFormulario
          id="auditoria-ip"
          etiqueta={t('auditoria.ipOrigen')}
          maxLength={45}
          valor={borrador.ip_origen}
          onCambiar={(valor) => cambiar('ip_origen', valor)}
          error={errores.ip_origen}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={4} xl={2}>
        <CampoFormulario
          id="auditoria-desde"
          etiqueta={t('auditoria.desde')}
          type="date"
          valor={borrador.fecha_desde}
          onCambiar={(valor) => cambiar('fecha_desde', valor)}
          error={errores.fecha_desde}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={4} xl={2}>
        <CampoFormulario
          id="auditoria-hasta"
          etiqueta={t('auditoria.hasta')}
          type="date"
          valor={borrador.fecha_hasta}
          onCambiar={(valor) => cambiar('fecha_hasta', valor)}
          error={errores.fecha_hasta}
          className="mb-0"
        />
      </Col>
    </BarraFiltros>
  );
}
