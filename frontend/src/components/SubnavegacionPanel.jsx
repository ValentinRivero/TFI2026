import Nav from 'react-bootstrap/Nav';
import { Link, useLocation } from 'react-router-dom';
import { t } from '../i18n/index.js';
import { enlaceActivo } from '../utils/navegacion.js';

/**
 * Subnavegación interna del panel. `secciones` es `[{ a, texto }]` (las que el rol puede ver); la activa sale de la
 * ruta actual y es una sola. `/panel` coincide solo de forma exacta, porque es la raíz del resto.
 */
export default function SubnavegacionPanel({ secciones }) {
  const { pathname } = useLocation();
  const activa = enlaceActivo(pathname, secciones.map(({ a }) => a));

  return (
    <Nav variant="tabs" className="mb-4 subnavegacion-panel" as="nav" aria-label={t('panel.subnavegacion')}>
      {secciones.map(({ a, texto }) => (
        <Nav.Item key={a}>
          <Nav.Link
            as={Link}
            to={a}
            active={activa === a}
            aria-current={activa === a ? 'page' : undefined}
          >
            {texto}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  );
}
