import { t } from '../i18n/index.js';
import AuditoriaRow from './AuditoriaRow.jsx';
import ListaAdmin from './ListaAdmin.jsx';

const COLUMNAS = [
  { clave: 'fecha', etiqueta: t('auditoria.columnas.fecha') },
  { clave: 'evento', etiqueta: t('auditoria.columnas.evento') },
  { clave: 'detalle', etiqueta: t('auditoria.columnas.detalle') },
  { clave: 'usuario', etiqueta: t('auditoria.columnas.usuario') },
  { clave: 'complejo', etiqueta: t('auditoria.columnas.complejo') },
  { clave: 'ip', etiqueta: t('auditoria.columnas.ip') },
];

/** Eventos de auditoría en una tabla paginada con sus estados (carga, error, vacío). `lista` viene de `useListaPaginada`. */
export default function TablaAuditoria({ lista }) {
  return (
    <ListaAdmin
      lista={lista}
      columnas={COLUMNAS}
      etiqueta={t('auditoria.titulo')}
      resumen={t('auditoria.resumen', { total: lista.total })}
      errorTitulo={t('auditoria.errorTitulo')}
      vacio={{ titulo: t('auditoria.vacioTitulo'), descripcion: t('auditoria.vacioDescripcion') }}
      renderFila={(evento) => <AuditoriaRow key={evento.id} evento={evento} />}
    />
  );
}
