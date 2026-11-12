import { Link } from 'react-router-dom';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { formatearPrecio } from '../utils/formatos.js';
import Icono from './Icono.jsx';

/** Tarjeta del catálogo: nombre, dirección, deportes, servicios y precio mínimo, con acceso al detalle. */
export default function ComplejoCard({ complejo }) {
  const { id, nombre, direccion, deportes = [], servicios = [], precio_desde: precioDesde } = complejo;
  const visibles = servicios.slice(0, PARAMETROS.catalogo.serviciosEnTarjeta);
  const ocultos = servicios.length - visibles.length;

  return (
    <article className="card h-100">
      <div className="card-body d-flex flex-column">
        <h2 className="h4 card-title mb-1">
          <Link to={`/complejos/${id}`} className="text-reset text-decoration-none stretched-link">{nombre}</Link>
        </h2>
        <p className="text-secondary mb-2 d-flex align-items-start gap-1">
          <Icono nombre="ubicacion" tamano={16} className="flex-shrink-0 mt-1" />
          <span>{direccion}</span>
        </p>
        <div className="d-flex flex-wrap gap-2 mb-2">
          {deportes.length > 0
            ? deportes.map((deporte) => <span key={deporte.id} className="badge badge-info">{deporte.nombre}</span>)
            : <span className="small text-secondary">{t('tarjeta.sinDeportes')}</span>}
        </div>
        {visibles.length > 0 && (
          <div className="d-flex flex-wrap gap-2 mb-3">
            {visibles.map((servicio) => <span key={servicio.id} className="badge badge-neutro">{servicio.nombre}</span>)}
            {ocultos > 0 && <span className="badge badge-neutro">{t('tarjeta.masServicios', { cantidad: ocultos })}</span>}
          </div>
        )}
        <p className="mt-auto mb-3">
          {precioDesde === null || precioDesde === undefined ? (
            <span className="text-secondary">{t('tarjeta.sinPrecio')}</span>
          ) : (
            <>
              {t('tarjeta.desde')} <span className="num fs-5">{formatearPrecio(precioDesde)}</span> {t('tarjeta.porTurno')}
            </>
          )}
        </p>
        <span className="btn btn-primary w-100 position-relative" aria-hidden="true">{t('tarjeta.verTurnos')}</span>
      </div>
    </article>
  );
}
