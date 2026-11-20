import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import Cargando from './Cargando.jsx';
import SelectorPermisos from './SelectorPermisos.jsx';

const { limitesCampos } = PARAMETROS;

/**
 * Alta y edición de un rol personalizado en un diálogo: nombre, descripción opcional y selector de permisos. `formulario`
 * y `permisos` son lo que devuelve `useRolesSistema`. Un rechazo del backend (nombre repetido, permisos exclusivos de la
 * plataforma) se ve bajo el campo o, si no es de un campo, arriba.
 */
export default function ModalRol({ formulario, permisos }) {
  const { abierto, editando, valores, errores, error, enviando } = formulario;
  const campo = (nombre) => ({ valor: valores[nombre], onCambiar: (valor) => formulario.cambiar(nombre, valor), error: errores[nombre] });
  const errorGeneral = error && !errores.nombre && !errores.descripcion && !errores.permisos;

  return (
    <Modal show={abierto} onHide={formulario.cerrar} centered backdrop="static" size="lg" scrollable>
      <Form onSubmit={formulario.guardar} noValidate className="d-flex flex-column overflow-hidden">
        <Modal.Header closeButton closeLabel={t('comun.cerrar')}>
          <Modal.Title as="h2" className="h4">{t(editando ? 'roles.tituloEdicion' : 'roles.tituloAlta')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {errorGeneral && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <CampoFormulario
            id="rol-nombre"
            etiqueta={t('roles.campoNombre')}
            maxLength={limitesCampos.nombreRol}
            autoComplete="off"
            ayuda={t('roles.ayudaNombre', { minimo: PARAMETROS.cuenta.nombreLargoMinimo, maximo: limitesCampos.nombreRol })}
            {...campo('nombre')}
          />
          <CampoFormulario
            id="rol-descripcion"
            etiqueta={t('roles.campoDescripcion')}
            maxLength={limitesCampos.descripcionRol}
            autoComplete="off"
            {...campo('descripcion')}
          />
          <h3 className="h5">{t('roles.permisos')}</h3>
          <p className="small text-secondary">{t('roles.ayudaPermisos')}</p>
          {errores.permisos && <Alerta variante="danger">{errores.permisos}</Alerta>}
          {permisos.cargando && <Cargando variante="seccion" />}
          {permisos.error && (
            <AlertaReintento titulo={t('roles.errorPermisos')} mensaje={permisos.error.mensaje} onReintentar={permisos.recargar} />
          )}
          {!permisos.cargando && !permisos.error && (
            <SelectorPermisos
              permisos={permisos.items}
              seleccionados={valores.permisos}
              onAlternar={formulario.alternar}
              idBase="rol-permiso"
            />
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={formulario.cerrar}>{t('comun.cancelar')}</Button>
          <BotonAccion type="submit" cargando={enviando} disabled={permisos.cargando || Boolean(permisos.error)} textoCargando={t('comun.guardando')}>
            {t('comun.guardar')}
          </BotonAccion>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
