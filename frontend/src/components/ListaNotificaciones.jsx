import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';
import EstadoVacio from './EstadoVacio.jsx';
import NotificacionRow from './NotificacionRow.jsx';

/**
 * Notificaciones de una bandeja con todos sus estados: carga, error con reintento, vacío y filas con "Mostrar más".
 * `lista` es lo que devuelve `useBandejaNotificaciones`; `vacio` es `{ titulo, descripcion }` del estado sin
 * resultados; `onMarcarLeida` recibe la notificación que se quiere marcar.
 */
export default function ListaNotificaciones({
  lista,
  vacio,
  etiqueta,
  errorTitulo = t('notificaciones.errorTitulo'),
  mostrarResumen = true,
  onMarcarLeida,
}) {
  const { items, total, hayMas, cargando, cargandoMas, error, errorMas, cargarMas, recargar } = lista;

  return (
    <section aria-label={etiqueta} aria-busy={cargando}>
      {cargando && <Cargando variante="seccion" />}

      {!cargando && error && <AlertaReintento titulo={errorTitulo} mensaje={error.mensaje} onReintentar={recargar} />}

      {!cargando && !error && items.length === 0 && (
        <EstadoVacio titulo={vacio.titulo} descripcion={vacio.descripcion} />
      )}

      {!cargando && !error && items.length > 0 && (
        <>
          {mostrarResumen && (
            <p className="text-secondary small" role="status">
              {t('notificaciones.resumen', { mostradas: items.length, total })}
            </p>
          )}
          <div className="d-grid gap-3">
            {items.map((notificacion) => (
              <NotificacionRow key={notificacion.id} notificacion={notificacion} onMarcarLeida={onMarcarLeida} />
            ))}
          </div>
          {errorMas && (
            <Alerta variante="warning" className="mt-3">{t('notificaciones.errorMas')} {errorMas.mensaje}</Alerta>
          )}
          {hayMas && (
            <div className="text-center mt-4">
              <BotonAccion variant="outline-primary" cargando={cargandoMas} onClick={cargarMas}>
                {t('comun.mostrarMas')}
              </BotonAccion>
            </div>
          )}
        </>
      )}
    </section>
  );
}
