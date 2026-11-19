import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Form from 'react-bootstrap/Form';
import Row from 'react-bootstrap/Row';
import { ESTADO_RESERVA, ESTADOS_RESERVA_FILTRABLES, opcionesDe, PERIODOS_AGENDA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_ESTADO = opcionesDe(ESTADO_RESERVA, ESTADOS_RESERVA_FILTRABLES);

/**
 * Filtros de la agenda: un día o, con la casilla "Rango de fechas", un desde y un hasta con un desplegable de períodos
 * rápidos (`periodo` es el que coincide con el rango, o vacío si es a mano); además cancha, estado y reservas con
 * conflicto de operatoria. `errores` son los avisos por campo del rango y `onCambiar(campo, valor)` avisa cada cambio.
 */
export default function FiltrosAgenda({
  filtros,
  errores = {},
  periodo = '',
  canchas,
  onCambiar,
  onAlternarRango,
  onElegirPeriodo,
  onLimpiar,
}) {
  const opcionesPeriodo = PERIODOS_AGENDA.map(({ valor, clave }) => ({ valor, etiqueta: t(clave) }));

  return (
    <Row as="form" className="g-3 align-items-end mb-3" role="search" aria-label={t('agenda.filtros')} onSubmit={(evento) => evento.preventDefault()}>
      {filtros.conRango ? (
        <>
          <Col sm={6} lg={3} xl={2}>
            <CampoFormulario
              id="agenda-filtro-desde"
              etiqueta={t('agenda.desde')}
              type="date"
              valor={filtros.fecha_desde}
              onCambiar={(valor) => onCambiar('fecha_desde', valor)}
              error={errores.fecha_desde}
              className="mb-0"
            />
          </Col>
          <Col sm={6} lg={3} xl={2}>
            <CampoFormulario
              id="agenda-filtro-hasta"
              etiqueta={t('agenda.hasta')}
              type="date"
              valor={filtros.fecha_hasta}
              onCambiar={(valor) => onCambiar('fecha_hasta', valor)}
              error={errores.fecha_hasta}
              className="mb-0"
            />
          </Col>
          <Col sm={6} lg={3} xl={2}>
            <CampoSelect
              id="agenda-filtro-periodo"
              etiqueta={t('agenda.periodo')}
              valor={periodo}
              onCambiar={onElegirPeriodo}
              placeholder={t('agenda.periodoPlaceholder')}
              opciones={opcionesPeriodo}
              className="mb-0"
            />
          </Col>
        </>
      ) : (
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
      )}
      <Col sm={6} lg={3} xl={2}>
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
      <Col sm={6} lg={3} xl={2}>
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
      <Col sm={6} lg={3} xl={3}>
        <Form.Check
          id="agenda-filtro-rango"
          type="checkbox"
          label={t('agenda.rangoDeFechas')}
          checked={filtros.conRango}
          onChange={(evento) => onAlternarRango(evento.target.checked)}
        />
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
