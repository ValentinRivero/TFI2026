import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { opcionesDe, TIPO_MOTIVO_EXCEPCION, VIGENCIA_EXCEPCION } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_MOTIVO = opcionesDe(TIPO_MOTIVO_EXCEPCION);

/** Filtros del listado de excepciones: vigencia, cancha, motivo y un día cubierto. `onCambiar(campo, valor)`. */
export default function FiltrosExcepciones({ filtros, canchas, onCambiar, onLimpiar }) {
  const vigencias = [
    { valor: VIGENCIA_EXCEPCION.VIGENTES, etiqueta: t('excepciones.vigentes') },
    { valor: VIGENCIA_EXCEPCION.FINALIZADAS, etiqueta: t('excepciones.finalizadas') },
  ];

  return (
    <Row className="g-3 align-items-end mb-3" as="form" role="search" aria-label={t('excepciones.filtros')} onSubmit={(evento) => evento.preventDefault()}>
      <Col sm={6} lg={3} xl={2}>
        <CampoSelect
          id="filtro-vigencia"
          etiqueta={t('excepciones.vigencia')}
          valor={filtros.vigencia}
          onCambiar={(valor) => onCambiar('vigencia', valor)}
          placeholder={t('excepciones.todas')}
          opciones={vigencias}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={3}>
        <CampoSelect
          id="filtro-cancha"
          etiqueta={t('excepciones.cancha')}
          valor={filtros.cancha}
          onCambiar={(valor) => onCambiar('cancha', valor)}
          placeholder={t('excepciones.todasLasCanchas')}
          opciones={canchas.map((cancha) => ({ valor: String(cancha.id), etiqueta: cancha.nombre }))}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={3}>
        <CampoSelect
          id="filtro-motivo"
          etiqueta={t('excepciones.motivo')}
          valor={filtros.motivo}
          onCambiar={(valor) => onCambiar('motivo', valor)}
          placeholder={t('excepciones.todosLosMotivos')}
          opciones={OPCIONES_MOTIVO}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3} xl={2}>
        <CampoFormulario
          id="filtro-fecha"
          etiqueta={t('excepciones.fecha')}
          type="date"
          valor={filtros.fecha}
          onCambiar={(valor) => onCambiar('fecha', valor)}
          className="mb-0"
        />
      </Col>
      <Col xs="auto">
        <Button variant="outline-secondary" onClick={onLimpiar}>{t('excepciones.limpiarFiltros')}</Button>
      </Col>
    </Row>
  );
}
