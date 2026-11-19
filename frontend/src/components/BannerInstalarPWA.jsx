import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { MODO_BANNER_INSTALAR } from '../utils/pwa.js';
import BotonAccion from './BotonAccion.jsx';
import Icono from './Icono.jsx';

/**
 * Invitación a instalar la aplicación. `modo` viene de `useInstalacionPwa`: `'instalar'` (Chromium y Android, con el
 * botón que abre el aviso nativo), `'ios'` (indicación manual del menú Compartir) o `null` (no se muestra).
 */
export default function BannerInstalarPWA({ modo, onInstalar, onCerrar }) {
  if (!modo) return null;
  const nativo = modo === MODO_BANNER_INSTALAR;

  return (
    <aside className="banner-pwa" role="region" aria-label={t('pwa.aviso')}>
      <div className="banner-pwa-contenido">
        <span className="banner-pwa-icono" aria-hidden="true">
          <Icono nombre={nativo ? 'descargar' : 'compartir'} tamano={22} />
        </span>
        <div className="banner-pwa-texto">
          <strong className="d-block">{t('pwa.titulo')}</strong>
          <span>{nativo ? t('pwa.instalarDescripcion') : t('pwa.iosDescripcion')}</span>
        </div>
        <div className="banner-pwa-acciones">
          {nativo && <BotonAccion size="sm" onClick={onInstalar}>{t('pwa.instalar')}</BotonAccion>}
          <Button
            variant="outline-light"
            size="sm"
            className="banner-pwa-cerrar"
            onClick={onCerrar}
            aria-label={t('pwa.cerrar')}
            title={t('pwa.cerrar')}
          >
            <Icono nombre="cerrar" tamano={18} />
          </Button>
        </div>
      </div>
    </aside>
  );
}
