import { t } from '../i18n/index.js';
import ListaNotificaciones from './ListaNotificaciones.jsx';

/**
 * Bloque destacado con los avisos urgentes sin leer, encima de la bandeja. `lista` es lo que devuelve
 * `useBandejaNotificaciones` filtrada por urgentes pendientes; sin avisos muestra una línea tranquilizadora o, con
 * `ocultarSiVacio`, solo aparece cuando hay avisos pendientes (o un error al cargarlos). `nombresDeComplejos` se pasa a las filas.
 */
export default function AvisosUrgentes({ lista, nombresDeComplejos, ocultarSiVacio = false, onMarcarLeida }) {
  const pendientes = lista.items.length;
  if (ocultarSiVacio && !lista.error && pendientes === 0) return null;

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
        nombresDeComplejos={nombresDeComplejos}
        vacio={{ titulo: t('notificaciones.urgentesVacio') }}
        onMarcarLeida={onMarcarLeida}
      />
    </section>
  );
}
