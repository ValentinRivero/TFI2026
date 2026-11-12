import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosAuditoria from '../components/FiltrosAuditoria.jsx';
import TablaAuditoria from '../components/TablaAuditoria.jsx';
import useAuditoria from '../hooks/useAuditoria.js';
import { t } from '../i18n/index.js';

/**
 * Registro de eventos de seguridad y de negocio (superadmin), del más reciente al más antiguo, con filtros por tipo,
 * usuario, complejo, IP de origen y rango de fechas.
 */
export default function Auditoria() {
  const auditoria = useAuditoria();

  return (
    <div>
      <EncabezadoPantalla titulo={t('auditoria.titulo')} descripcion={t('auditoria.descripcion')} />
      <FiltrosAuditoria filtros={auditoria.filtros} complejos={auditoria.complejos} />
      <TablaAuditoria lista={auditoria.lista} />
    </div>
  );
}
