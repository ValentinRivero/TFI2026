import Button from 'react-bootstrap/Button';
import { Link } from 'react-router-dom';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

/**
 * Pantalla de estado a pantalla completa del contenido (acceso restringido, página no encontrada): una tarjeta
 * centrada con un emblema circular, el título, una explicación formal y el botón para volver al inicio, centrado.
 * `icono` es el nombre de un trazo de `Icono.jsx`.
 */
export default function PantallaEstado({ icono, titulo, descripcion }) {
  return (
    <section className="pantalla-estado" aria-labelledby="titulo-pantalla-estado">
      <div className="superficie pantalla-estado-tarjeta">
        <span className="pantalla-estado-emblema" aria-hidden="true">
          <Icono nombre={icono} tamano={36} />
        </span>
        <h1 id="titulo-pantalla-estado" className="pantalla-estado-titulo">{titulo}</h1>
        <p className="text-secondary mb-0">{descripcion}</p>
        <div className="pantalla-estado-acciones">
          <Button as={Link} to="/" variant="primary" size="lg" className="d-inline-flex align-items-center gap-2">
            <Icono nombre="inicio" tamano={20} />
            {t('comun.volverAlInicio')}
          </Button>
        </div>
      </div>
    </section>
  );
}
