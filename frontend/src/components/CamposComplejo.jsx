import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';

const { limitesCampos, panel } = PARAMETROS;

/**
 * Campos del perfil comercial de un complejo: nombre, dirección, coordenadas, teléfono, límite de cancelación e
 * información de la seña. Los comparten la configuración del complejo y el alta de un complejo nuevo. `campo(nombre)`
 * devuelve las propiedades de cada control (`valor`, `onCambiar`, `error` y, en solo lectura, `disabled`).
 */
export default function CamposComplejo({ campo, prefijo = 'complejo' }) {
  return (
    <Row className="g-3">
      <Col md={6}>
        <CampoFormulario id={`${prefijo}-nombre`} etiqueta={t('configuracion.nombre')} maxLength={limitesCampos.nombre} className="mb-0" {...campo('nombre')} />
      </Col>
      <Col md={6}>
        <CampoFormulario id={`${prefijo}-direccion`} etiqueta={t('configuracion.direccion')} maxLength={limitesCampos.direccion} className="mb-0" {...campo('direccion')} />
      </Col>
      <Col sm={6} md={3}>
        <CampoFormulario
          id={`${prefijo}-latitud`}
          etiqueta={t('configuracion.latitud')}
          inputMode="decimal"
          className="mb-0"
          {...campo('latitud')}
        />
      </Col>
      <Col sm={6} md={3}>
        <CampoFormulario
          id={`${prefijo}-longitud`}
          etiqueta={t('configuracion.longitud')}
          inputMode="decimal"
          className="mb-0"
          {...campo('longitud')}
        />
      </Col>
      <Col md={6}>
        <CampoFormulario
          id={`${prefijo}-telefono`}
          etiqueta={t('configuracion.telefono')}
          type="tel"
          inputMode="tel"
          maxLength={limitesCampos.telefono}
          className="mb-0"
          {...campo('telefono_contacto')}
        />
      </Col>
      <Col xs={12}>
        <Form.Text muted>{t('configuracion.ayudaCoordenadas')}</Form.Text>
      </Col>
      <Col md={6}>
        <CampoFormulario
          id={`${prefijo}-horas`}
          etiqueta={t('configuracion.horasLimite')}
          type="number"
          min={0}
          max={panel.horasCancelacionMaximas}
          inputMode="numeric"
          ayuda={t('configuracion.ayudaHoras')}
          className="mb-0"
          {...campo('horas_limite_cancelacion')}
        />
      </Col>
      <Col md={6}>
        <CampoFormulario
          id={`${prefijo}-sena`}
          etiqueta={t('configuracion.infoSena')}
          as="textarea"
          rows={2}
          maxLength={limitesCampos.infoSena}
          ayuda={t('configuracion.ayudaInfoSena')}
          className="mb-0"
          {...campo('info_sena')}
        />
      </Col>
    </Row>
  );
}
