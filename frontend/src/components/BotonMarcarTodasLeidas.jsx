import { t } from '../i18n/index.js';
import BotonAccion from './BotonAccion.jsx';

/**
 * Acción "Marcar todas como leídas" de la bandeja. Se deshabilita mientras la petición está en curso (lo resuelve
 * `BotonAccion`) y, si `sinLeer` es 0, no se muestra: no hay nada que marcar.
 */
export default function BotonMarcarTodasLeidas({ sinLeer, onClick }) {
  if (!(sinLeer > 0)) return null;
  return (
    <BotonAccion variant="outline-secondary" textoCargando={t('notificaciones.marcandoTodas')} onClick={onClick}>
      {t('notificaciones.marcarTodasLeidas')}
    </BotonAccion>
  );
}
