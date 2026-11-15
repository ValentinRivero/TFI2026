import { t } from '../i18n/index.js';
import ListaNotificaciones from './ListaNotificaciones.jsx';

/**
 * Bloque destacado con los avisos urgentes sin leer del complejo, encima de la bandeja. `lista` es lo que devuelve
 * `useBandejaNotificaciones` filtrada por urgentes pendientes; sin avisos muestra una línea tranquilizadora.
 */
export default function AvisosUrgentes({ lista, onMarcarLeida }) {
  const pendientes = lista.items.length;

  return (
    <section className="bloque-urgente p-3 mb-4" aria-labelledby="avisos-urgentes-titulo">
      <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
        <h2 id="avisos-urgentes-titulo" className="h5 mb-0">{t('notificaciones.urgentesTitulo')}</h2>
        {pendientes > 0 && <span className="badge badge-peligro num">{lista.total}</span>}
      </div>
      <p className="text-secondary small mb-3">{t('notificaciones.urgentesDescripcion')}</p>
      <ListaNotificaciones
        lista={lista}
        etiqueta={t('notificaciones.urgentesTitulo')}
        errorTitulo={t('notificaciones.urgentesErrorTitulo')}
        mostrarResumen={false}
        vacio={{ titulo: t('notificaciones.urgentesVacio') }}
        onMarcarLeida={onMarcarLeida}
      />
    </section>
  );
}
