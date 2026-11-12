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
import CampoSelect from './CampoSelect.jsx';
import SelectorSlotCancha from './SelectorSlotCancha.jsx';

/**
 * Alta de una reserva telefónica o presencial (presentación): cancha, día, horario (casillero libre de la grilla real) y datos del cliente.
 * `formulario` es lo que devuelve `useAgenda` en `alta`; `canchas` es `[{ id, nombre }]` del complejo. El horario de
 * fin y el precio los calcula el servidor según la cancha.
 */
export default function FormularioReservaManual({ formulario, canchas }) {
  const { valores, errores, error, enviando, hoy, cambiar, enviar, cerrar } = formulario;
  const campo = (nombre) => ({ valor: valores[nombre], onCambiar: (valor) => cambiar(nombre, valor), error: errores[nombre] });

  return (
    <Card body className="mb-4">
      <h2 className="h5 mb-3">{t('agenda.altaTitulo')}</h2>
      <Form onSubmit={enviar} noValidate>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        <Row className="g-3">
          <Col md={4}>
            <CampoSelect
              id="reserva-manual-cancha"
              etiqueta={t('agenda.cancha')}
              placeholder={t('agenda.elegirCancha')}
              opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
              className="mb-0"
              {...campo('cancha')}
            />
          </Col>
          <Col sm={6} md={4}>
            <CampoFormulario id="reserva-manual-fecha" etiqueta={t('agenda.fechaTurno')} type="date" min={hoy} className="mb-0" {...campo('fecha_turno')} />
          </Col>
          <Col xs={12}>
            <SelectorSlotCancha
              bloques={formulario.bloques}
              valor={valores.hora_inicio}
              onElegir={(hora) => cambiar('hora_inicio', hora)}
              error={errores.hora_inicio}
            />
          </Col>
          <Col md={6}>
            <CampoFormulario
              id="reserva-manual-nombre"
              etiqueta={t('agenda.nombreCliente')}
              maxLength={PARAMETROS.limitesCampos.nombre}
              className="mb-0"
              {...campo('nombre_cliente_manual')}
            />
          </Col>
          <Col md={6}>
            <CampoFormulario
              id="reserva-manual-telefono"
              etiqueta={t('agenda.telefonoCliente')}
              type="tel"
              inputMode="tel"
              maxLength={PARAMETROS.limitesCampos.telefono}
              className="mb-0"
              {...campo('telefono_cliente_manual')}
            />
          </Col>
          <Col xs={12}>
            <CampoFormulario
              id="reserva-manual-observaciones"
              etiqueta={t('agenda.observaciones')}
              as="textarea"
              rows={2}
              maxLength={PARAMETROS.limitesCampos.descripcion}
              ayuda={t('agenda.ayudaObservaciones')}
              className="mb-0"
              {...campo('observaciones')}
            />
          </Col>
        </Row>
        <div className="d-flex flex-wrap gap-2 mt-4">
          <BotonAccion type="submit" cargando={enviando} textoCargando={t('agenda.registrando')}>
            {t('agenda.registrar')}
          </BotonAccion>
          <Button variant="outline-secondary" onClick={cerrar} disabled={enviando}>{t('comun.cancelar')}</Button>
        </div>
      </Form>
    </Card>
  );
}
