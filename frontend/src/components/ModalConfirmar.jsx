import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import { t } from '../i18n/index.js';
import BotonAccion from './BotonAccion.jsx';

/**
 * Diálogo de confirmación. `onConfirmar` puede devolver una promesa: mientras se resuelve, el botón queda
 * deshabilitado con `Cargando`. `confirmarDeshabilitado` lo bloquea mientras no se pueda confirmar (datos sin cargar,
 * operación impedida). Es la base de las confirmaciones explícitas de la operatoria (conflictos, reaperturas).
 */
export default function ModalConfirmar({
  mostrar,
  titulo,
  children,
  onConfirmar,
  onCancelar,
  textoConfirmar,
  textoCancelar,
  variante = 'primary',
  confirmarDeshabilitado = false,
}) {
  return (
    <Modal show={mostrar} onHide={onCancelar} centered backdrop="static">
      <Modal.Header closeButton closeLabel={t('comun.cerrar')}>
        <Modal.Title as="h2" className="h4">{titulo}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{children}</Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onCancelar}>{textoCancelar ?? t('comun.cancelar')}</Button>
        <BotonAccion variant={variante} disabled={confirmarDeshabilitado} onClick={onConfirmar}>
          {textoConfirmar ?? t('comun.confirmar')}
        </BotonAccion>
      </Modal.Footer>
    </Modal>
  );
}
