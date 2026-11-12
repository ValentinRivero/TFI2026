import Nav from 'react-bootstrap/Nav';
import { t } from '../i18n/index.js';

/** Selector entre las reservas del día y los turnos fijos. `pestanas` es `[{ valor, clave }]`; `activa` es un `valor`. */
export default function PestanasAgenda({ pestanas, activa, onCambiar }) {
  return (
    <Nav variant="tabs" className="mb-4" activeKey={activa} onSelect={onCambiar} aria-label={t('agenda.vistas')}>
      {pestanas.map(({ valor, clave }) => (
        <Nav.Item key={valor}>
          <Nav.Link as="button" type="button" eventKey={valor} aria-current={valor === activa ? 'page' : undefined}>
            {t(clave)}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  );
}
