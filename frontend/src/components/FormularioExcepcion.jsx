import Card from 'react-bootstrap/Card';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { ES_DIA_COMPLETO, opcionesDe, TIPO_MOTIVO_EXCEPCION } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_MOTIVO = opcionesDe(TIPO_MOTIVO_EXCEPCION);

const opcionesAlcance = () => [
  { valor: 'complejo', etiqueta: t('excepciones.alcanceComplejo') },
  { valor: 'cancha', etiqueta: t('excepciones.alcanceCancha') },
];

const opcionesTipo = () => [
  { valor: String(ES_DIA_COMPLETO), etiqueta: t('excepciones.tipoDiaCompleto') },
  { valor: '0', etiqueta: t('excepciones.tipoFranja') },
];

/**
 * Alta de una excepción horaria (presentación): alcance (todo el complejo o una cancha), tipo de cierre (día completo
 * o franja), fechas, horas, motivo y descripción. `formulario` es lo que devuelve `useExcepciones`; `canchas` es
 * `[{ id, nombre }]` del complejo.
 */
export default function FormularioExcepcion({ formulario, canchas }) {
  const { valores, errores, error, enviando, hoy, cambiar, enviar } = formulario;
  const franja = Number(valores.es_dia_completo) !== ES_DIA_COMPLETO;
  const campo = (nombre) => ({ valor: valores[nombre], onCambiar: (valor) => cambiar(nombre, valor), error: errores[nombre] });

  return (
    <Card body className="mb-4">
      <h2 className="h5 mb-3">{t('excepciones.registrarTitulo')}</h2>
      <Form onSubmit={enviar} noValidate>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        <Row className="g-3">
          <Col md={4}>
            <CampoSelect id="excepcion-alcance" etiqueta={t('excepciones.alcance')} opciones={opcionesAlcance()} className="mb-0" {...campo('alcance')} />
          </Col>
          {valores.alcance === 'cancha' && (
            <Col md={4}>
              <CampoSelect
                id="excepcion-cancha"
                etiqueta={t('excepciones.cancha')}
                placeholder={t('excepciones.elegirCancha')}
                opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
                className="mb-0"
                {...campo('cancha')}
              />
            </Col>
          )}
          <Col md={4}>
            <CampoSelect id="excepcion-tipo" etiqueta={t('excepciones.tipo')} opciones={opcionesTipo()} className="mb-0" {...campo('es_dia_completo')} />
          </Col>
          <Col sm={6} md={3}>
            <CampoFormulario id="excepcion-inicio" etiqueta={t('excepciones.fechaInicio')} type="date" min={hoy} className="mb-0" {...campo('fecha_inicio')} />
          </Col>
          <Col sm={6} md={3}>
            <CampoFormulario id="excepcion-fin" etiqueta={t('excepciones.fechaFin')} type="date" min={valores.fecha_inicio || hoy} className="mb-0" {...campo('fecha_fin')} />
          </Col>
          {franja && (
            <>
              <Col sm={6} md={3}>
                <CampoFormulario id="excepcion-hora-inicio" etiqueta={t('excepciones.horaInicio')} type="time" className="mb-0" {...campo('hora_inicio')} />
              </Col>
              <Col sm={6} md={3}>
                <CampoFormulario id="excepcion-hora-fin" etiqueta={t('excepciones.horaFin')} type="time" className="mb-0" {...campo('hora_fin')} />
              </Col>
            </>
          )}
          <Col md={4}>
            <CampoSelect
              id="excepcion-motivo"
              etiqueta={t('excepciones.motivo')}
              placeholder={t('excepciones.elegirMotivo')}
              opciones={OPCIONES_MOTIVO}
              className="mb-0"
              {...campo('tipo_motivo')}
            />
          </Col>
          <Col md={8}>
            <CampoFormulario
              id="excepcion-descripcion"
              etiqueta={t('excepciones.descripcionCampo')}
              maxLength={PARAMETROS.limitesCampos.descripcion}
              ayuda={t('excepciones.ayudaDescripcion')}
              className="mb-0"
              {...campo('descripcion')}
            />
          </Col>
        </Row>
        <div className="mt-4">
          <BotonAccion type="submit" cargando={enviando} textoCargando={t('excepciones.registrando')}>
            {t('excepciones.registrar')}
          </BotonAccion>
        </div>
      </Form>
    </Card>
  );
}
