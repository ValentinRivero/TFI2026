import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';
import { t } from '../i18n/index.js';
import SelectorPermisos from './SelectorPermisos.jsx';

/**
 * Permisos de un rol en modo consulta (también los de un rol base, que no se editan). `ficha` es lo que devuelve
 * `useRolesSistema`: el `rol` abierto, o `null` con el diálogo cerrado.
 */
export default function ModalPermisosRol({ ficha }) {
  const { rol } = ficha;

  return (
    <Modal show={Boolean(rol)} onHide={ficha.cerrar} centered scrollable>
      <Modal.Header closeButton closeLabel={t('comun.cerrar')}>
        <Modal.Title as="h2" className="h4">{t('roles.fichaTitulo', { nombre: rol?.nombre ?? '' })}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {rol?.es_base && <p className="small text-secondary">{t('roles.fichaBase')}</p>}
        {rol && rol.permisos.length === 0 && <p className="text-secondary mb-0">{t('roles.sinPermisos')}</p>}
        {rol && rol.permisos.length > 0 && (
          <SelectorPermisos
            permisos={rol.permisos}
            seleccionados={rol.permisos.map((permiso) => permiso.id)}
            soloLectura
            idBase="ficha-permiso"
          />
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={ficha.cerrar}>{t('comun.cerrar')}</Button>
      </Modal.Footer>
    </Modal>
  );
}
