import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { t } from '../i18n/index.js';

/**
 * Barra de filtros con borrador: los campos (`children`, normalmente `Col` con un control cada uno) no consultan hasta
 * enviar el formulario con "Buscar" o Enter. `onAplicar` recibe el evento y `onLimpiar` restablece los filtros.
 */
export default function BarraFiltros({ etiqueta, onAplicar, onLimpiar, textoAplicar, children }) {
  return (
    <Row as="form" className="g-3 align-items-end mb-3" role="search" aria-label={etiqueta} onSubmit={onAplicar} noValidate>
      {children}
      <Col xs="auto" className="d-flex gap-2">
        <Button type="submit">{textoAplicar ?? t('comun.buscar')}</Button>
        <Button variant="outline-secondary" onClick={onLimpiar}>{t('comun.limpiarFiltros')}</Button>
      </Col>
    </Row>
  );
}
