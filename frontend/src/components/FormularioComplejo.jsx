import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';

const { limitesCampos, panel } = PARAMETROS;

/**
 * Perfil comercial del complejo (presentación): dirección, coordenadas, teléfono, límite de cancelación e
 * información de la seña. Con `soloLectura` los campos se muestran atenuados y deshabilitados (sin foco ni selección) y no hay botones.
 * El estado lo maneja `useConfiguracionComplejo`; `errores` es un texto por campo y `error`, el `ErrorApi` del envío.
 */
export default function FormularioComplejo({
  valores,
  errores,
  onCambiar,
  onEnviar,
  onDescartar,
  enviando,
  hayCambios,
  error,
  guardado,
  soloLectura = false,
}) {
  const campo = (nombre) => ({
    valor: valores[nombre],
    onCambiar: (valor) => onCambiar(nombre, valor),
    error: errores[nombre],
    disabled: soloLectura,
    tabIndex: soloLectura ? -1 : undefined,
  });

  return (
    <Card body className="mb-4">
      <h2 className="h5 mb-3">{t('configuracion.datos')}</h2>
      <Form onSubmit={onEnviar} noValidate>
        <fieldset disabled={soloLectura} className={`border-0 p-0 m-0${soloLectura ? ' solo-lectura' : ''}`}>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        {guardado && <Alerta variante="success">{t('configuracion.guardado')}</Alerta>}
        <Row className="g-3">
          <Col md={6}>
            <CampoFormulario id="complejo-nombre" etiqueta={t('configuracion.nombre')} maxLength={limitesCampos.nombre} className="mb-0" {...campo('nombre')} />
          </Col>
          <Col md={6}>
            <CampoFormulario id="complejo-direccion" etiqueta={t('configuracion.direccion')} maxLength={limitesCampos.direccion} className="mb-0" {...campo('direccion')} />
          </Col>
          <Col sm={6} md={3}>
            <CampoFormulario
              id="complejo-latitud"
              etiqueta={t('configuracion.latitud')}
              inputMode="decimal"
              className="mb-0"
              {...campo('latitud')}
            />
          </Col>
          <Col sm={6} md={3}>
            <CampoFormulario
              id="complejo-longitud"
              etiqueta={t('configuracion.longitud')}
              inputMode="decimal"
              className="mb-0"
              {...campo('longitud')}
            />
          </Col>
          <Col md={6}>
            <CampoFormulario
              id="complejo-telefono"
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
              id="complejo-horas"
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
              id="complejo-sena"
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
        </fieldset>
        {!soloLectura && (
          <div className="d-flex flex-wrap gap-2 mt-4">
            <BotonAccion type="submit" cargando={enviando} disabled={!hayCambios} textoCargando={t('configuracion.guardando')}>
              {t('comun.guardar')}
            </BotonAccion>
            <Button variant="outline-secondary" disabled={!hayCambios || enviando} onClick={onDescartar}>
              {t('configuracion.descartar')}
            </Button>
          </div>
        )}
      </Form>
    </Card>
  );
}
