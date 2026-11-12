import { describir, TIPO_EVENTO_AUDITORIA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaHora } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';
import UsuarioEnAuditoria from './UsuarioEnAuditoria.jsx';

const columnas = 'auditoria.columnas';

/** Fila del registro de auditoría: momento, tipo de evento, acción y detalle, usuario (solo por id, con su resumen emergente), complejo e IP de origen. */
export default function AuditoriaRow({ evento }) {
  const { etiqueta, badge } = describir(TIPO_EVENTO_AUDITORIA, evento.tipo_evento);

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.fecha`)} className="num">{formatearFechaHora(evento.fecha_accion)}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.evento`)}>
        <span className={`badge ${badge}`}>{etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.detalle`)} className="texto-multilinea">
        <div>{evento.accion}</div>
        {evento.detalle && <div className="small text-secondary">{evento.detalle}</div>}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.usuario`)}>
        {evento.usuario ? <UsuarioEnAuditoria usuarioId={evento.usuario} complejoNombre={evento.complejo_nombre} /> : '-'}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.complejo`)}>{evento.complejo_nombre || '-'}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.ip`)} className="num">{evento.ip_origen || '-'}</CeldaTabla>
    </tr>
  );
}
