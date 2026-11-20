import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { CATALOGOS_SISTEMA } from '../utils/catalogoSistema.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';

/**
 * Alta y cambio de nombre de un deporte o servicio en un diálogo. `formulario` es lo que devuelve
 * `useCatalogoSistema`; el error del nombre (local o del backend, por ejemplo un nombre repetido) se ve bajo el campo y
 * cualquier otro rechazo, arriba.
 */
export default function ModalNombreCatalogo({ recurso, formulario }) {
  const { abierto, editando, nombre, errores, error, enviando } = formulario;
  const { textos, largoMaximo } = CATALOGOS_SISTEMA[recurso];

  return (
    <Modal show={abierto} onHide={formulario.cerrar} centered backdrop="static">
      <Form onSubmit={formulario.guardar} noValidate>
        <Modal.Header closeButton closeLabel={t('comun.cerrar')}>
          <Modal.Title as="h2" className="h4">{t(`${textos}.${editando ? 'tituloEdicion' : 'tituloAlta'}`)}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {error && !errores.nombre && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <CampoFormulario
            id="catalogo-nombre"
            etiqueta={t(`${textos}.campoNombre`)}
            maxLength={largoMaximo}
            autoComplete="off"
            valor={nombre}
            onCambiar={formulario.cambiarNombre}
            error={errores.nombre}
            ayuda={t('catalogoSistema.ayudaNombre', { minimo: PARAMETROS.cuenta.nombreLargoMinimo, maximo: largoMaximo })}
            className="mb-0"
          />
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={formulario.cerrar}>{t('comun.cancelar')}</Button>
          <BotonAccion type="submit" cargando={enviando} textoCargando={t('comun.guardando')}>
            {t('comun.guardar')}
          </BotonAccion>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
