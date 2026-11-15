import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import {
  CATEGORIA_NOTIFICACION,
  FILTRO_ESTADO_NOTIFICACION,
  opcionesDe,
  PRIORIDAD_NOTIFICACION,
} from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_PRIORIDAD = opcionesDe(PRIORIDAD_NOTIFICACION);
const OPCIONES_CATEGORIA = opcionesDe(CATEGORIA_NOTIFICACION);

/**
 * Filtros de una bandeja de notificaciones. `campos` elige cuáles se ofrecen (`estado`, `prioridad`, `categoria`);
 * `onCambiar(campo, valor)` avisa cada cambio y `onLimpiar` vuelve a los valores por defecto.
 */
export default function FiltrosNotificaciones({
  filtros,
  campos = ['estado', 'prioridad', 'categoria'],
  hayFiltros,
  onCambiar,
  onLimpiar,
}) {
  const opcionesEstado = Object.values(FILTRO_ESTADO_NOTIFICACION).map(({ valor, clave }) => ({
    valor,
    etiqueta: t(clave),
  }));

  return (
    <Row
      as="form"
      className="g-3 align-items-end mb-3"
      role="search"
      aria-label={t('notificaciones.filtros')}
      onSubmit={(evento) => evento.preventDefault()}
    >
      {campos.includes('estado') && (
        <Col sm={6} lg={3}>
          <CampoSelect
            id="filtro-notificacion-estado"
            etiqueta={t('notificaciones.estado')}
            valor={filtros.estado}
            onCambiar={(valor) => onCambiar('estado', valor)}
            opciones={opcionesEstado}
            className="mb-0"
          />
        </Col>
      )}
      {campos.includes('prioridad') && (
        <Col sm={6} lg={3}>
          <CampoSelect
            id="filtro-notificacion-prioridad"
            etiqueta={t('notificaciones.prioridad')}
            valor={filtros.prioridad}
            onCambiar={(valor) => onCambiar('prioridad', valor)}
            placeholder={t('notificaciones.todasLasPrioridades')}
            opciones={OPCIONES_PRIORIDAD}
            className="mb-0"
          />
        </Col>
      )}
      {campos.includes('categoria') && (
        <Col sm={6} lg={3}>
          <CampoSelect
            id="filtro-notificacion-categoria"
            etiqueta={t('notificaciones.categoria')}
            valor={filtros.categoria}
            onCambiar={(valor) => onCambiar('categoria', valor)}
            placeholder={t('notificaciones.todasLasCategorias')}
            opciones={OPCIONES_CATEGORIA}
            className="mb-0"
          />
        </Col>
      )}
      {hayFiltros && (
        <Col xs="auto">
          <Button variant="outline-secondary" onClick={onLimpiar}>{t('comun.limpiarFiltros')}</Button>
        </Col>
      )}
    </Row>
  );
}
