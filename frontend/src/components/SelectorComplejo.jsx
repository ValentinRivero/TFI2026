import Form from 'react-bootstrap/Form';
import { describir, ESTADO_CONTRATO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';

/**
 * Complejo activo del panel. Con más de uno ofrece una lista para cambiarlo; con uno solo lo muestra como título.
 * El estado del contrato queda a la vista porque un contrato suspendido o pendiente oculta el complejo del catálogo.
 */
export default function SelectorComplejo({ complejos, activo, onElegir }) {
  const { etiqueta, badge } = describir(ESTADO_CONTRATO, activo.estado_contrato);

  return (
    <div className="d-flex flex-wrap align-items-center gap-2 gap-md-3">
      {complejos.length > 1 ? (
        <Form.Group controlId="panel-complejo" className="d-flex align-items-center gap-2 mb-0">
          <Form.Label className="mb-0 text-secondary">{t('panel.elegirComplejo')}</Form.Label>
          <Form.Select
            value={activo.id}
            onChange={(evento) => onElegir(Number(evento.target.value))}
            className="selector-complejo"
          >
            {complejos.map((complejo) => (
              <option key={complejo.id} value={complejo.id}>{complejo.nombre}</option>
            ))}
          </Form.Select>
        </Form.Group>
      ) : (
        <p className="h4 mb-0">{activo.nombre}</p>
      )}
      <span className={`badge ${badge}`}>{t('panel.contrato')}: {etiqueta}</span>
    </div>
  );
}
