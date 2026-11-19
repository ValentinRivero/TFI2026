import OverlayTrigger from 'react-bootstrap/OverlayTrigger';
import Popover from 'react-bootstrap/Popover';
import { Link } from 'react-router-dom';
import { t } from '../i18n/index.js';
import ResumenUsuario from './ResumenUsuario.jsx';

/**
 * Identificación de un usuario en la auditoría: `Usuario #<id>` (el registro no muestra el correo). Al pasar el mouse o
 * enfocar abre un recuadro con su resumen y, al hacer clic, lleva a su ficha en modo consulta (`/sistema?verUsuario=`).
 */
export default function UsuarioEnAuditoria({ usuarioId, complejoNombre }) {
  const recuadro = (
    <Popover id={`resumen-usuario-${usuarioId}`}>
      <Popover.Header as="h3" className="h6">{t('usuarios.resumenCuenta')}</Popover.Header>
      <Popover.Body>
        <ResumenUsuario usuarioId={usuarioId} complejoNombre={complejoNombre} />
      </Popover.Body>
    </Popover>
  );

  return (
    <OverlayTrigger trigger={['hover', 'focus']} placement="right" overlay={recuadro}>
      <Link to={`/sistema?verUsuario=${encodeURIComponent(usuarioId)}`} className="num">
        {t('auditoria.usuarioId', { id: usuarioId })}
      </Link>
    </OverlayTrigger>
  );
}
