import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import Row from 'react-bootstrap/Row';
import {
  COBERTURA,
  DURACION_TURNO,
  ESTADO_CANCHA,
  ESTADOS_CANCHA_EDITABLES,
  ILUMINACION,
  opcionesDe,
  TIPO_SUPERFICIE,
} from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES = {
  superficie: opcionesDe(TIPO_SUPERFICIE),
  cobertura: opcionesDe(COBERTURA),
  iluminacion: opcionesDe(ILUMINACION),
  duracion: opcionesDe(DURACION_TURNO),
  estado: opcionesDe(ESTADO_CANCHA, ESTADOS_CANCHA_EDITABLES),
};

/**
 * Alta y edición de una cancha en un diálogo. `formulario` es lo que devuelve `useGestionCanchas` (valores, errores
 * por campo, error general y acciones); `deportes` es el catálogo `[{ id, nombre }]`. El estado solo se elige al editar.
 */
export default function ModalCancha({ formulario, deportes }) {
  const { abierto, editando, valores, errores, error, enviando, cambiar, enviar, cerrar } = formulario;
  const opcionesDeporte = deportes.map((deporte) => ({ valor: String(deporte.id), etiqueta: deporte.nombre }));
  const campo = (nombre) => ({ valor: valores[nombre], onCambiar: (valor) => cambiar(nombre, valor), error: errores[nombre] });

  return (
    <Modal show={abierto} onHide={cerrar} centered backdrop="static" size="lg">
      <Form onSubmit={enviar} noValidate>
        <Modal.Header closeButton closeLabel={t('comun.cerrar')}>
          <Modal.Title as="h2" className="h4">
            {t(editando ? 'gestionCanchas.tituloEdicion' : 'gestionCanchas.tituloAlta')}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <Row className="g-3">
            <Col md={6}>
              <CampoFormulario
                id="cancha-nombre"
                etiqueta={t('gestionCanchas.nombre')}
                maxLength={PARAMETROS.limitesCampos.nombreCancha}
                className="mb-0"
                {...campo('nombre')}
              />
            </Col>
            <Col md={6}>
              <CampoSelect
                id="cancha-deporte"
                etiqueta={t('gestionCanchas.deporte')}
                placeholder={t('gestionCanchas.elegirDeporte')}
                opciones={opcionesDeporte}
                className="mb-0"
                {...campo('deporte')}
              />
            </Col>
            <Col md={4}>
              <CampoSelect id="cancha-superficie" etiqueta={t('gestionCanchas.superficie')} opciones={OPCIONES.superficie} className="mb-0" {...campo('tipo_superficie')} />
            </Col>
            <Col md={4}>
              <CampoSelect id="cancha-cobertura" etiqueta={t('gestionCanchas.cobertura')} opciones={OPCIONES.cobertura} className="mb-0" {...campo('cobertura')} />
            </Col>
            <Col md={4}>
              <CampoSelect id="cancha-iluminacion" etiqueta={t('gestionCanchas.iluminacion')} opciones={OPCIONES.iluminacion} className="mb-0" {...campo('iluminacion')} />
            </Col>
            <Col md={4}>
              <CampoSelect id="cancha-duracion" etiqueta={t('gestionCanchas.duracion')} opciones={OPCIONES.duracion} className="mb-0" {...campo('duracion_turno_min')} />
            </Col>
            <Col md={4}>
              <CampoFormulario
                id="cancha-precio"
                etiqueta={t('gestionCanchas.precio')}
                inputMode="decimal"
                ayuda={t('gestionCanchas.ayudaPrecio')}
                className="mb-0"
                {...campo('precio_base')}
              />
            </Col>
            {editando && (
              <Col md={4}>
                <CampoSelect id="cancha-estado" etiqueta={t('gestionCanchas.estado')} opciones={OPCIONES.estado} className="mb-0" {...campo('estado')} />
              </Col>
            )}
          </Row>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={cerrar}>{t('comun.cancelar')}</Button>
          <BotonAccion type="submit" cargando={enviando} textoCargando={t('gestionCanchas.guardando')}>
            {t('comun.guardar')}
          </BotonAccion>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
