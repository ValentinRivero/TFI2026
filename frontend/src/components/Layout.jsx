import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import Offcanvas from 'react-bootstrap/Offcanvas';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { ETIQUETA_ROL, puedeVer } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { logout } from '../services/authService.js';
import BotonAccion from './BotonAccion.jsx';

// Enlaces de la sesión según la sección y el rol: `puedeVer` decide qué se muestra; los backends deciden qué se permite.
const SECCIONES_DE_SESION = [
  { seccion: 'misReservas', a: '/mis-reservas', texto: 'navegacion.misReservas' },
  { seccion: 'panel', a: '/panel', texto: 'navegacion.panel' },
  { seccion: 'reportes', a: '/panel/reportes', texto: 'navegacion.reportes' },
  { seccion: 'sistema', a: '/sistema', texto: 'navegacion.sistema' },
  { seccion: 'notificaciones', a: '/notificaciones', texto: 'navegacion.notificaciones' },
  { seccion: 'perfil', a: '/perfil', texto: 'navegacion.perfil' },
];

/**
 * Estructura común de las pantallas: barra superior en pizarra con el estado de la sesión, menú que pasa a un panel
 * lateral en móvil, contenido principal y pie. `enlaces` suma accesos propios de la pantalla (`{ a, texto }`);
 * `ancho` admite `panel` para los paneles de administración (contenedor fluido y densidad de escritorio).
 */
export default function Layout({ enlaces = [], ancho = 'normal', children }) {
  const esPanel = ancho === 'panel';
  const { autenticado, usuario, rol } = useSesion();
  const navegar = useNavigate();

  const cerrarSesion = async () => {
    await logout();
    navegar('/');
  };

  return (
    <div className="d-flex flex-column min-vh-100">
      <a className="salto-contenido" href="#contenido">{t('navegacion.saltar')}</a>
      <Navbar expand="lg" className="barra-superior" variant="dark">
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
            <Offcanvas.Body className="d-lg-flex align-items-lg-center">
              <Nav className="ms-lg-auto align-items-lg-center">
                {enlaces.map(({ a, texto }) => (
                  <Nav.Link key={a} as={NavLink} to={a} end>{texto}</Nav.Link>
                ))}
                {autenticado && SECCIONES_DE_SESION.filter(({ seccion }) => puedeVer(seccion, rol)).map(({ a, texto }) => (
                  <Nav.Link key={a} as={NavLink} to={a} end>{t(texto)}</Nav.Link>
                ))}
              </Nav>
              {autenticado ? (
                <div className="d-flex flex-column flex-lg-row align-items-lg-center gap-2 ms-lg-3 mt-3 mt-lg-0">
                  <span className="text-white small" aria-label={t('navegacion.sesionDe', { nombre: usuario.nombre_completo })}>
                    {t('sesion.comoRol', { nombre: usuario.nombre_completo, rol: ETIQUETA_ROL[rol] ?? rol ?? '' })}
                  </span>
                  <BotonAccion variant="outline-light" size="sm" onClick={cerrarSesion}>
                    {t('navegacion.cerrarSesion')}
                  </BotonAccion>
                </div>
              ) : (
                <div className="d-flex flex-column flex-lg-row gap-2 ms-lg-3 mt-3 mt-lg-0">
                  <Button as={Link} to="/login" variant="outline-light" size="sm">{t('navegacion.ingresar')}</Button>
                  <Button as={Link} to="/registro" variant="primary" size="sm">{t('navegacion.registrarse')}</Button>
                </div>
              )}
            </Offcanvas.Body>
          </Navbar.Offcanvas>
        </Container>
      </Navbar>

      <main id="contenido" className={`flex-grow-1 py-4${esPanel ? ' panel-admin' : ''}`}>
        <Container fluid={esPanel}>{children}</Container>
      </main>

      <footer className="pie-pagina py-3">
        <Container fluid={esPanel} className="d-flex flex-wrap justify-content-between gap-2">
          <span>{t('marca.eslogan')}</span>
          <Link to="/privacidad">{t('navegacion.privacidad')}</Link>
        </Container>
      </footer>
    </div>
  );
}
