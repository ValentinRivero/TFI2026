import { Suspense, useEffect, useRef, useState } from 'react';
import Button from 'react-bootstrap/Button';
import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ETIQUETA_ROL, puedeVer } from '../config/catalogos.js';
import useSesion from '../hooks/useSesion.js';
import { t } from '../i18n/index.js';
import { enlaceActivo } from '../utils/navegacion.js';
import { logout } from '../services/authService.js';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';

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
 * Estructura común de las pantallas: barra superior en pizarra con tres zonas (marca, secciones centradas y sesión),
 * que en móvil pasa a un panel flotante anclado bajo el botón del menú, contenido principal y pie. El límite de
 * `Suspense` envuelve solo el contenido: mientras carga una pantalla diferida la barra y el menú siguen en su lugar. `enlaces` suma accesos propios de la pantalla (`{ a, texto }`);
 * `ancho` admite `panel` para los paneles de administración (contenedor fluido y densidad de escritorio).
 * `claveCarga` fija el límite de carga: por defecto cambia con la ruta; un panel con subvistas propias lo fija para
 * que su estructura (selector, subnavegación) no se vuelva a montar al pasar de una subvista a otra.
 */
export default function Layout({ enlaces = [], ancho = 'normal', claveCarga, children }) {
  const esPanel = ancho === 'panel';
  const { autenticado, usuario, rol } = useSesion();
  const navegar = useNavigate();
  const { pathname } = useLocation();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const barra = useRef(null);

  const seccionesVisibles = autenticado ? SECCIONES_DE_SESION.filter(({ seccion }) => puedeVer(seccion, rol)) : [];
  // El enlace activo sale de la ruta actual y es uno solo: no depende del foco ni del historial del navegador.
  const activo = enlaceActivo(pathname, ['/', ...enlaces.map(({ a }) => a), ...seccionesVisibles.map(({ a }) => a)]);

  // Al cambiar de ruta (logo, "Atrás") el foco puede quedar en el enlace anterior: se suelta si ya no es el activo.
  useEffect(() => {
    const retenido = barra.current?.querySelector('.barra-secciones .nav-link:focus:not(.active)');
    if (retenido) retenido.blur();
  }, [pathname]);

  // El panel flotante del móvil se cierra al tocar fuera de la barra o con Escape.
  useEffect(() => {
    if (!menuAbierto) return undefined;
    const fuera = (evento) => {
      if (!barra.current?.contains(evento.target)) setMenuAbierto(false);
    };
    const escape = (evento) => {
      if (evento.key === 'Escape') setMenuAbierto(false);
    };
    document.addEventListener('pointerdown', fuera);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('pointerdown', fuera);
      document.removeEventListener('keydown', escape);
    };
  }, [menuAbierto]);

  const cerrarSesion = async () => {
    setMenuAbierto(false);
    await logout();
    navegar('/', { replace: true });
  };

  return (
    <div className="d-flex flex-column min-vh-100">
      <a className="salto-contenido" href="#contenido">{t('navegacion.saltar')}</a>
      <Navbar
        ref={barra}
        expand="lg"
        className="barra-superior"
        variant="dark"
        expanded={menuAbierto}
        onToggle={setMenuAbierto}
        collapseOnSelect
      >
        <Container fluid>
          <Navbar.Brand as={Link} to="/" onClick={() => setMenuAbierto(false)}>
            <img src="/icons/logo.svg" alt="" width="32" height="32" />
            {t('marca.nombre')}
          </Navbar.Brand>
          <Navbar.Toggle
            aria-controls="menu-principal"
            aria-label={t('navegacion.menu')}
            aria-expanded={menuAbierto}
            className="barra-hamburguesa d-lg-none"
          >
            <span className="barra-hamburguesa-icono" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </Navbar.Toggle>
          <Navbar.Collapse id="menu-principal" className="menu-principal">
            <Nav className="barra-secciones" aria-label={t('navegacion.principal')}>
              <Nav.Link as={Link} to="/" eventKey="/" active={activo === '/'} aria-current={activo === '/' ? 'page' : undefined}>
                {t('navegacion.inicio')}
              </Nav.Link>
              {enlaces.map(({ a, texto }) => (
                <Nav.Link key={a} as={Link} to={a} eventKey={a} active={activo === a} aria-current={activo === a ? 'page' : undefined}>
                  {texto}
                </Nav.Link>
              ))}
              {seccionesVisibles.map(({ a, texto }) => (
                <Nav.Link key={a} as={Link} to={a} eventKey={a} active={activo === a} aria-current={activo === a ? 'page' : undefined}>
                  {t(texto)}
                </Nav.Link>
              ))}
            </Nav>
            {autenticado ? (
              <div className="barra-sesion">
                <span className="barra-usuario" aria-label={t('navegacion.sesionDe', { nombre: usuario.nombre_completo })}>
                  {t('sesion.comoRol', { nombre: usuario.nombre_completo, rol: ETIQUETA_ROL[rol] ?? rol ?? '' })}
                </span>
                <BotonAccion variant="outline-light" size="sm" onClick={cerrarSesion}>
                  {t('navegacion.cerrarSesion')}
                </BotonAccion>
              </div>
            ) : (
              <div className="barra-sesion">
                <Button as={Link} to="/login" variant="outline-light" size="sm">{t('navegacion.ingresar')}</Button>
                <Button as={Link} to="/registro" variant="primary" size="sm">{t('navegacion.registrarse')}</Button>
              </div>
            )}
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <main id="contenido" className={`flex-grow-1 py-4 position-relative${esPanel ? ' panel-admin' : ''}`}>
        {/* `key` crea un límite nuevo por pantalla: así la carga de una ruta diferida muestra el overlay también al navegar. */}
        <Suspense key={claveCarga ?? pathname} fallback={<Cargando variante="superpuesto" />}>
          <Container fluid={esPanel}>{children}</Container>
        </Suspense>
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
