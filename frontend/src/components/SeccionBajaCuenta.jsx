import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';

/** Zona de baja de la cuenta: explica qué implica y ofrece iniciar el flujo con vista previa. */
export default function SeccionBajaCuenta({ onSolicitar }) {
  return (
    <section className="superficie p-3 mt-4" aria-labelledby="perfil-baja-titulo">
      <h2 id="perfil-baja-titulo" className="h5">{t('perfil.bajaTitulo')}</h2>
      <p className="text-secondary">{t('perfil.bajaDescripcion')}</p>
      <Button variant="outline-danger" onClick={onSolicitar}>{t('perfil.bajaSolicitar')}</Button>
    </section>
  );
}
