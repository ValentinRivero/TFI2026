import { Link } from 'react-router-dom';
import { t } from '../i18n/index.js';
import { textoContador } from '../utils/notificaciones.js';
import Icono from './Icono.jsx';

/**
 * Campana de la barra superior: lleva a la bandeja personal y muestra cuántas notificaciones hay sin leer. `contador`
 * es `null` mientras no se conoce (o si el servicio no responde): entonces no hay badge. `activa` resalta la campana
 * cuando se está en la bandeja y `onNavegar` cierra el menú móvil.
 */
export default function CampanaNotificaciones({ contador, activa, onNavegar }) {
  const sinLeer = contador > 0;
  const etiqueta = sinLeer ? t('notificaciones.campana', { cantidad: contador }) : t('navegacion.notificaciones');

  return (
    <Link
      to="/notificaciones"
      className={`campana${activa ? ' campana-activa' : ''}`}
      aria-label={etiqueta}
      aria-current={activa ? 'page' : undefined}
      onClick={onNavegar}
    >
      <Icono nombre="campana" />
      <span className="campana-texto d-lg-none">{t('navegacion.notificaciones')}</span>
      {sinLeer && <span className="campana-badge num" aria-hidden="true">{textoContador(contador)}</span>}
    </Link>
  );
}
