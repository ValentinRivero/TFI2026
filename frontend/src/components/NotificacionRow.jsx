import {
  CATEGORIA_NOTIFICACION,
  describir,
  NOTIFICACION_NO_LEIDA,
  PRIORIDAD_NOTIFICACION,
} from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaHora } from '../utils/formatos.js';
import { esUrgente } from '../utils/notificaciones.js';
import BotonAccion from './BotonAccion.jsx';

/**
 * Una notificación: categoría, prioridad, mensaje, fecha y hora, y estado. La urgente se distingue por un borde y por
 * su etiqueta, no solo por el color. Si está sin leer y recibe `onMarcarLeida` ofrece marcarla como leída.
 */
export default function NotificacionRow({ notificacion, onMarcarLeida }) {
  const categoria = describir(CATEGORIA_NOTIFICACION, notificacion.categoria);
  const prioridad = describir(PRIORIDAD_NOTIFICACION, notificacion.prioridad);
  const sinLeer = notificacion.estado === NOTIFICACION_NO_LEIDA;
  const clases = [
    'superficie',
    'notificacion',
    'p-3',
    esUrgente(notificacion) && 'notificacion-urgente',
    sinLeer && 'notificacion-sin-leer',
  ].filter(Boolean).join(' ');

  return (
    <article className={clases}>
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
        <div className="d-flex flex-wrap align-items-center gap-2">
          <span className={`badge ${categoria.badge}`}>{categoria.etiqueta}</span>
          <span className={`badge ${prioridad.badge}`}>{prioridad.etiqueta}</span>
          {sinLeer && <span className="badge badge-info">{t('notificaciones.sinLeer')}</span>}
        </div>
        <time className="small text-secondary num" dateTime={notificacion.fecha_creacion ?? undefined}>
          {formatearFechaHora(notificacion.fecha_creacion)}
        </time>
      </div>
      <p className="notificacion-mensaje mb-0">{notificacion.mensaje}</p>
      {sinLeer && onMarcarLeida && (
        <div className="mt-3">
          <BotonAccion variant="outline-secondary" size="sm" onClick={() => onMarcarLeida(notificacion)}>
            {t('notificaciones.marcarLeida')}
          </BotonAccion>
        </div>
      )}
    </article>
  );
}
