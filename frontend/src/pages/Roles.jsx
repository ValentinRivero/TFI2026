import Button from 'react-bootstrap/Button';
import Alerta from '../components/Alerta.jsx';
import BarraBusquedaLocal from '../components/BarraBusquedaLocal.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import ListaUsos from '../components/ListaUsos.jsx';
import ModalConfirmarAccion from '../components/ModalConfirmarAccion.jsx';
import ModalPermisosRol from '../components/ModalPermisosRol.jsx';
import ModalRol from '../components/ModalRol.jsx';
import ModalUsos from '../components/ModalUsos.jsx';
import TablaRoles from '../components/TablaRoles.jsx';
import useDetalleDeUsos from '../hooks/useDetalleDeUsos.js';
import useRolesSistema from '../hooks/useRolesSistema.js';
import { t } from '../i18n/index.js';

/**
 * Roles del sistema (superadmin): los base se consultan y los personalizados se crean, editan, dan de baja y
 * reactivan. Un rol personalizado solo recibe permisos que no son exclusivos de la plataforma. Los usos de cada rol
 * (las cuentas que lo tienen) se ven en un diálogo y enlazan con la ficha de cada cuenta.
 */
export default function Roles() {
  const roles = useRolesSistema();
  const { baja } = roles;
  const enUso = baja.objetivo && baja.objetivo.usos > 0;
  const detalle = useDetalleDeUsos('roles', baja.objetivo);

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
      {roles.hayItems && <BarraBusquedaLocal id="roles" etiquetaBusqueda={t('roles.buscar')} filtros={roles.filtros} />}
      <TablaRoles roles={roles} onVerUsos={detalle.abrir} />
      <ModalUsos tipo="roles" detalle={detalle} />
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
      >
        {enUso && <ListaUsos tipo="roles" usos={detalle.lista} />}
      </ModalConfirmarAccion>
    </div>
  );
}
