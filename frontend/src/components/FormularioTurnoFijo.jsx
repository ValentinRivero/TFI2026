import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { DIA_SEMANA, opcionesDe } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BotonAccion from './BotonAccion.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';
import SelectorBloquesHorarios from './SelectorBloquesHorarios.jsx';

const OPCIONES_DIA = opcionesDe(DIA_SEMANA);

/**
 * Alta de un turno fijo (presentación): cancha, día de la semana, hora de inicio, vigencia y datos del cliente. Sin
 * fecha de fin rige por tiempo indefinido. `formulario` es lo que devuelve `useTurnosFijos` en `alta`.
 */
export default function FormularioTurnoFijo({ formulario, canchas }) {
  const { valores, errores, error, enviando, hoy, cambiar, enviar, cerrar } = formulario;
  const campo = (nombre) => ({ valor: valores[nombre], onCambiar: (valor) => cambiar(nombre, valor), error: errores[nombre] });

  return (
    <Card body className="mb-4">
      <h2 className="h5 mb-3">{t('turnosFijos.altaTitulo')}</h2>
      <Form onSubmit={enviar} noValidate>
        {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
        <Row className="g-3">
          <Col md={4}>
            <CampoSelect
              id="turno-fijo-cancha"
              etiqueta={t('turnosFijos.cancha')}
              placeholder={t('turnosFijos.elegirCancha')}
              opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
              className="mb-0"
              {...campo('cancha')}
            />
          </Col>
          <Col sm={6} md={4}>
            <CampoSelect
              id="turno-fijo-dia"
              etiqueta={t('turnosFijos.dia')}
              placeholder={t('turnosFijos.elegirDia')}
              opciones={OPCIONES_DIA}
              className="mb-0"
              {...campo('dia_semana')}
            />
          </Col>
          <Col xs={12}>
            <SelectorBloquesHorarios
              bloques={formulario.bloques}
              valor={valores.hora_inicio}
              onElegir={(hora) => cambiar('hora_inicio', hora)}
              error={errores.hora_inicio}
            />
          </Col>
          <Col sm={6} md={4}>
            <CampoFormulario id="turno-fijo-desde" etiqueta={t('turnosFijos.vigenciaDesde')} type="date" min={hoy} className="mb-0" {...campo('fecha_inicio_vigencia')} />
          </Col>
          <Col sm={6} md={4}>
            <CampoFormulario
              id="turno-fijo-hasta"
              etiqueta={t('turnosFijos.vigenciaHasta')}
              type="date"
              min={valores.fecha_inicio_vigencia || hoy}
              ayuda={t('turnosFijos.ayudaSinFin')}
              className="mb-0"
              {...campo('fecha_fin_vigencia')}
            />
          </Col>
          <Col md={6}>
            <CampoFormulario
              id="turno-fijo-nombre"
              etiqueta={t('turnosFijos.nombreCliente')}
              maxLength={PARAMETROS.limitesCampos.nombre}
              className="mb-0"
              {...campo('nombre_cliente_manual')}
            />
          </Col>
          <Col md={6}>
            <CampoFormulario
              id="turno-fijo-telefono"
              etiqueta={t('turnosFijos.telefonoCliente')}
              type="tel"
              inputMode="tel"
              maxLength={PARAMETROS.limitesCampos.telefono}
              className="mb-0"
              {...campo('telefono_cliente_manual')}
            />
          </Col>
        </Row>
        <div className="d-flex flex-wrap gap-2 mt-4">
          <BotonAccion type="submit" cargando={enviando} textoCargando={t('turnosFijos.registrando')}>
            {t('turnosFijos.registrar')}
          </BotonAccion>
          <Button variant="outline-secondary" onClick={cerrar} disabled={enviando}>{t('comun.cancelar')}</Button>
        </div>
      </Form>
    </Card>
  );
}
