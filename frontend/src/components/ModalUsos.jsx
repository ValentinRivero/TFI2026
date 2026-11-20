import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import { t } from '../i18n/index.js';
import ListaUsos from './ListaUsos.jsx';

/**
 * Diálogo "Dónde está en uso" de un deporte, servicio o rol. `detalle` es lo que devuelve `useDetalleDeUsos`: `objetivo`
 * es el ítem abierto (o `null` con el diálogo cerrado) y `lista`, sus usos paginados.
 */
export default function ModalUsos({ tipo, detalle, onIrAlComplejo }) {
  const { objetivo } = detalle;

  return (
    <Modal show={objetivo !== null} onHide={detalle.cerrar} centered scrollable>
      <Modal.Header closeButton closeLabel={t('comun.cerrar')}>
        <Modal.Title as="h2" className="h4">{t('usos.titulo', { nombre: objetivo?.nombre ?? '' })}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {objetivo && <ListaUsos tipo={tipo} usos={detalle.lista} onIrAlComplejo={onIrAlComplejo} />}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={detalle.cerrar}>{t('comun.cerrar')}</Button>
      </Modal.Footer>
    </Modal>
  );
}
