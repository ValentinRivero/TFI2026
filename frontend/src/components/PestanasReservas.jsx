import Nav from 'react-bootstrap/Nav';
import { PESTANAS_RESERVA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';

/** Selector entre las reservas por jugar y el historial. `activa` y `onCambiar` usan el valor de `vigencia`. */
export default function PestanasReservas({ activa, onCambiar }) {
  return (
    <Nav variant="tabs" className="mb-3" activeKey={activa} onSelect={onCambiar} aria-label={t('misReservas.vistas')}>
      {PESTANAS_RESERVA.map(({ valor, clave }) => (
        <Nav.Item key={valor}>
          <Nav.Link as="button" type="button" eventKey={valor} aria-current={valor === activa ? 'page' : undefined}>
            {t(clave)}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  );
}
