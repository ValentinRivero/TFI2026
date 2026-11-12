import Col from 'react-bootstrap/Col';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import { Link } from 'react-router-dom';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

const { app, politica, pie } = PARAMETROS;

// Solo se publica una red con una dirección https configurada: un valor vacío o de otro esquema se descarta.
const redesPublicadas = pie.redes.filter(({ url }) => typeof url === 'string' && url.startsWith('https://'));

/**
 * Pie de página (presentación): marca y ubicación, redes (con su usuario) y política de privacidad con su versión
 * vigente (junto al contacto, para no alargar el pie), contacto por correo y la versión de la aplicación. Las redes y el correo se leen de `config/parametros.js`. Se apila en pantallas
 * chicas y pasa a tres columnas desde `md`. `ancho` es el de `Layout` (`panel` usa el contenedor fluido).
 */
export default function PiePagina({ ancho = 'normal' }) {
  const anio = new Date().getFullYear();

  return (
    <footer className="pie-pagina" aria-label={t('pie.etiqueta')}>
      <Container fluid={ancho === 'panel'} className="py-4">
        <Row className="g-4">
          <Col xs={12} md={4} lg={4}>
            <span className="pie-pagina-marca">
              <img src="/icons/logo.svg" alt="" width="32" height="32" />
              {t('marca.nombre')}
            </span>
            <p className="mt-3 mb-2">{t('pie.descripcion')}</p>
            <p className="d-flex align-items-center gap-2 mb-0">
              <Icono nombre="ubicacion" tamano={18} />
              {t('pie.ubicacion')}
            </p>
          </Col>

          <Col xs={12} sm={6} md={4} lg={4}>
            <h2 className="pie-pagina-titulo">{t('pie.redes')}</h2>
            <ul className="pie-pagina-lista">
              {redesPublicadas.map(({ clave, icono, usuario, url }) => (
                <li key={clave}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="pie-pagina-enlace pie-pagina-red"
                    aria-label={t('pie.abrirRed', { red: t(`pie.red.${clave}`), usuario })}
                  >
                    <span className="pie-pagina-canal"><Icono nombre={icono} tamano={14} /></span>
                    <span>{usuario}</span>
                  </a>
                </li>
              ))}
            </ul>
          </Col>

          <Col xs={12} sm={6} md={4} lg={4}>
            <h2 className="pie-pagina-titulo">{t('pie.contacto')}</h2>
            <p className="mb-3">
              <a href={`mailto:${politica.contacto}`} className="pie-pagina-enlace">
                <Icono nombre="correo" tamano={18} />
                <span>{politica.contacto}</span>
              </a>
            </p>
            <h2 className="pie-pagina-titulo mt-4">{t('pie.legal')}</h2>
            <ul className="pie-pagina-lista">
              <li>
                <Link to="/privacidad" className="pie-pagina-enlace">{t('pie.privacidad')}</Link>
                <span className="pie-pagina-nota"> - {politica.version}</span>
              </li>
            </ul>
          </Col>
        </Row>
      </Container>
      <div className="pie-pagina-legal">
        <Container fluid={ancho === 'panel'} className="py-3 small d-flex flex-wrap justify-content-between gap-2">
          <span>{t('pie.derechos', { anio })}</span>
          <span className="num">{t('pie.version', { version: app.version })}</span>
        </Container>
      </div>
    </footer>
  );
}
