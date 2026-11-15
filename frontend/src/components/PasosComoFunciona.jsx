import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { t } from '../i18n/index.js';
import Icono from './Icono.jsx';

const PASOS = Object.freeze([
  Object.freeze({ clave: 'elegir', icono: 'buscar' }),
  Object.freeze({ clave: 'consultar', icono: 'calendario' }),
  Object.freeze({ clave: 'reservar', icono: 'check' }),
]);

/** Franja de tres tarjetas con el recorrido de una reserva; se apilan en pantallas chicas. */
export default function PasosComoFunciona() {
  return (
    <section className="mb-4" aria-labelledby="pasos-titulo">
      <h2 id="pasos-titulo" className="visually-hidden">{t('portada.pasosTitulo')}</h2>
      <Row as="ol" className="g-3 list-unstyled mb-0">
        {PASOS.map(({ clave, icono }, indice) => (
          <Col as="li" key={clave} md={4}>
            <article className="superficie paso-card p-3 h-100">
              <div className="d-flex align-items-center gap-3 mb-2">
                <span className="paso-icono">
                  <Icono nombre={icono} tamano={22} />
                </span>
                <span className="paso-numero num">{t('portada.paso', { numero: indice + 1 })}</span>
              </div>
              <h3 className="h5 mb-1">{t(`portada.pasos.${clave}.titulo`)}</h3>
              <p className="text-secondary mb-0">{t(`portada.pasos.${clave}.descripcion`)}</p>
            </article>
          </Col>
        ))}
      </Row>
    </section>
  );
}
