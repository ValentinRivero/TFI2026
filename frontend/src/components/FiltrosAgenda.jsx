import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { ESTADO_RESERVA, ESTADOS_RESERVA_FILTRABLES, opcionesDe } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_ESTADO = opcionesDe(ESTADO_RESERVA, ESTADOS_RESERVA_FILTRABLES);

/** Filtros de la agenda: día, cancha, estado y reservas con conflicto de operatoria. `onCambiar(campo, valor)`. */
export default function FiltrosAgenda({ filtros, canchas, onCambiar, onLimpiar }) {
  return (
    <Row as="form" className="g-3 align-items-end mb-3" role="search" aria-label={t('agenda.filtros')} onSubmit={(evento) => evento.preventDefault()}>
      <Col sm={6} lg={3} xl={2}>
        <CampoFormulario
          id="agenda-filtro-fecha"
          etiqueta={t('agenda.fecha')}
          type="date"
          valor={filtros.fecha}
          onCambiar={(valor) => onCambiar('fecha', valor)}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={3}>
        <CampoSelect
          id="agenda-filtro-cancha"
          etiqueta={t('agenda.cancha')}
          valor={filtros.cancha}
          onCambiar={(valor) => onCambiar('cancha', valor)}
          placeholder={t('agenda.todasLasCanchas')}
          opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={3}>
        <CampoSelect
          id="agenda-filtro-estado"
          etiqueta={t('agenda.estado')}
          valor={filtros.estado}
          onCambiar={(valor) => onCambiar('estado', valor)}
          placeholder={t('agenda.todosLosEstados')}
          opciones={OPCIONES_ESTADO}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={2}>
        <Form.Check
          id="agenda-filtro-conflicto"
          type="checkbox"
          label={t('agenda.soloConflicto')}
          checked={filtros.conConflicto}
          onChange={(evento) => onCambiar('conConflicto', evento.target.checked)}
        />
      </Col>
      <Col xs="auto">
        <Button variant="outline-secondary" onClick={onLimpiar}>{t('comun.limpiarFiltros')}</Button>
      </Col>
    </Row>
  );
}
