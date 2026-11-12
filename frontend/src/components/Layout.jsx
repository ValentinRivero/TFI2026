import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Offcanvas from 'react-bootstrap/Offcanvas';
import { Link, NavLink } from 'react-router-dom';
import { t } from '../i18n/index.js';

/**
 * Estructura común de las pantallas: barra superior en pizarra con menú que pasa a un panel lateral en móvil,
 * contenido principal y pie. `enlaces` es una lista de `{ a, texto }`; `ancho` admite `panel` para los paneles de
 * administración (contenedor fluido y densidad de escritorio).
 */
export default function Layout({ enlaces = [], ancho = 'normal', children }) {
  const esPanel = ancho === 'panel';

  return (
    <div className="d-flex flex-column min-vh-100">
      <a className="salto-contenido" href="#contenido">{t('navegacion.saltar')}</a>
      <Navbar expand="md" className="barra-superior" variant="dark">
        <Container fluid={esPanel}>
          <Navbar.Brand as={Link} to="/">
            <img src="/icons/logo.svg" alt="" width="32" height="32" />
            {t('marca.nombre')}
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="menu-principal" aria-label={t('navegacion.menu')} />
          <Navbar.Offcanvas id="menu-principal" placement="end" className="menu-movil" aria-label={t('navegacion.principal')}>
            <Offcanvas.Header closeButton closeVariant="white">
              <Offcanvas.Title as="span" className="titulo text-white fs-4">{t('marca.nombre')}</Offcanvas.Title>
            </Offcanvas.Header>
            <Offcanvas.Body>
              <Nav className="ms-md-auto">
                {enlaces.map(({ a, texto }) => (
                  <Nav.Link key={a} as={NavLink} to={a} end>{texto}</Nav.Link>
                ))}
              </Nav>
            </Offcanvas.Body>
          </Navbar.Offcanvas>
        </Container>
      </Navbar>

      <main id="contenido" className={`flex-grow-1 py-4${esPanel ? ' panel-admin' : ''}`}>
        <Container fluid={esPanel}>{children}</Container>
      </main>

      <footer className="pie-pagina py-3">
        <Container fluid={esPanel}>{t('marca.eslogan')}</Container>
      </footer>
    </div>
  );
}
