import Card from 'react-bootstrap/Card';
import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';

/**
 * Servicios que ofrece el complejo (presentación): una casilla por servicio del catálogo. Con `soloLectura` se ven
 * las casillas sin poder cambiarlas. El estado lo maneja `useServiciosComplejo`.
 */
export default function SelectorServicios({
  catalogo,
  elegidos,
  cargando,
  errorCatalogo,
  onReintentar,
  onAlternar,
  onGuardar,
  enviando,
  hayCambios,
  error,
  guardado,
  soloLectura = false,
}) {
  return (
    <Card body className="mb-4">
      <h2 className="h5">{t('serviciosComplejo.titulo')}</h2>
      {!soloLectura && <p className="text-secondary">{t('serviciosComplejo.descripcion')}</p>}

      {cargando && <Cargando variante="seccion" />}
      {!cargando && errorCatalogo && (
        <AlertaReintento titulo={t('serviciosComplejo.errorCatalogo')} mensaje={errorCatalogo.mensaje} onReintentar={onReintentar} />
      )}
      {!cargando && !errorCatalogo && catalogo.length === 0 && (
        <p className="text-secondary mb-0">{t('serviciosComplejo.vacio')}</p>
      )}

      {!cargando && !errorCatalogo && catalogo.length > 0 && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          {guardado && <Alerta variante="success">{t('serviciosComplejo.guardado')}</Alerta>}
          <fieldset className="row g-2 mb-3" disabled={soloLectura}>
            <legend className="visually-hidden">{t('serviciosComplejo.titulo')}</legend>
            {catalogo.map((servicio) => (
              <div key={servicio.id} className="col-sm-6 col-lg-4">
                <Form.Check
                  type="checkbox"
                  id={`servicio-${servicio.id}`}
                  label={servicio.nombre}
                  checked={elegidos.includes(servicio.id)}
                  onChange={() => onAlternar(servicio.id)}
                />
              </div>
            ))}
          </fieldset>
          {!soloLectura && (
            <BotonAccion cargando={enviando} disabled={!hayCambios} onClick={onGuardar}>
              {t('serviciosComplejo.guardar')}
            </BotonAccion>
          )}
        </>
      )}
    </Card>
  );
}
