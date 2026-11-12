import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { DIA_SEMANA, ESTADO_TURNO_FIJO, opcionesDe, TURNO_FIJO_PAUSADO, TURNO_FIJO_VIGENTE } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_ESTADO = opcionesDe(ESTADO_TURNO_FIJO, [TURNO_FIJO_VIGENTE, TURNO_FIJO_PAUSADO]);
const OPCIONES_DIA = opcionesDe(DIA_SEMANA);

/** Filtros de los turnos fijos: cancha, estado y día de la semana. `onCambiar(campo, valor)`. */
export default function FiltrosTurnosFijos({ filtros, canchas, onCambiar, onLimpiar }) {
  return (
    <Row as="form" className="g-3 align-items-end mb-3" role="search" aria-label={t('turnosFijos.filtros')} onSubmit={(evento) => evento.preventDefault()}>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="turnos-filtro-cancha"
          etiqueta={t('turnosFijos.cancha')}
          valor={filtros.cancha}
          onCambiar={(valor) => onCambiar('cancha', valor)}
          placeholder={t('turnosFijos.todasLasCanchas')}
          opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="turnos-filtro-estado"
          etiqueta={t('turnosFijos.estado')}
          valor={filtros.estado}
          onCambiar={(valor) => onCambiar('estado', valor)}
          placeholder={t('turnosFijos.todosLosEstados')}
          opciones={OPCIONES_ESTADO}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="turnos-filtro-dia"
          etiqueta={t('turnosFijos.dia')}
          valor={filtros.dia}
          onCambiar={(valor) => onCambiar('dia', valor)}
          placeholder={t('turnosFijos.todosLosDias')}
          opciones={OPCIONES_DIA}
          className="mb-0"
        />
      </Col>
      <Col xs="auto">
        <Button variant="outline-secondary" onClick={onLimpiar}>{t('comun.limpiarFiltros')}</Button>
      </Col>
    </Row>
  );
}
