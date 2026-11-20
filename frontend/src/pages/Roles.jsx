import Button from 'react-bootstrap/Button';
import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import ModalConfirmarAccion from '../components/ModalConfirmarAccion.jsx';
import ModalPermisosRol from '../components/ModalPermisosRol.jsx';
import ModalRol from '../components/ModalRol.jsx';
import TablaRoles from '../components/TablaRoles.jsx';
import useRolesSistema from '../hooks/useRolesSistema.js';
import { t } from '../i18n/index.js';

/**
 * Roles del sistema (superadmin): los base se consultan y los personalizados se crean, editan, dan de baja y
 * reactivan. Un rol personalizado solo recibe permisos que no son exclusivos de la plataforma.
 */
export default function Roles() {
  const roles = useRolesSistema();
  const { baja } = roles;
  const enUso = baja.objetivo && baja.objetivo.usos > 0;

  return (
    <div>
      <EncabezadoPantalla
        titulo={t('roles.titulo')}
        descripcion={t('roles.descripcion')}
        acciones={<Button onClick={() => roles.formulario.abrir(null)}>{t('roles.nuevo')}</Button>}
      />
      {roles.aviso && <Alerta variante="success" onCerrar={roles.descartarAviso}>{roles.aviso}</Alerta>}
      {roles.errorReactivacion && (
        <Alerta variante="danger" onCerrar={roles.descartarErrorReactivacion}>{roles.errorReactivacion.mensaje}</Alerta>
      )}
      <TablaRoles roles={roles} />
      <ModalPermisosRol ficha={roles.ficha} />
      <ModalRol formulario={roles.formulario} permisos={roles.permisos} />
      <ModalConfirmarAccion
        abierto={baja.objetivo !== null}
        titulo={t('roles.bajaTitulo')}
        texto={baja.objetivo && t(enUso ? 'roles.bajaTextoEnUso' : 'roles.bajaTexto', {
          nombre: baja.objetivo.nombre,
          usos: baja.objetivo.usos,
        })}
        error={baja.error}
        textoConfirmar={t('roles.darDeBaja')}
        onConfirmar={baja.confirmar}
        onCancelar={baja.cerrar}
      />
    </div>
  );
}
