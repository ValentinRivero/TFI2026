import Button from 'react-bootstrap/Button';
import Col from 'react-bootstrap/Col';
import Row from 'react-bootstrap/Row';
import { FILTRO_ESTADO_REGISTRO } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_ESTADO = FILTRO_ESTADO_REGISTRO.map(({ valor, clave }) => ({ valor, etiqueta: t(clave) }));

/**
 * Búsqueda y filtro de estado de una lista que ya está en memoria: se aplican al escribir o elegir, sin pedir nada al
 * servidor. `filtros` es lo que devuelven `useCatalogoSistema` y `useRolesSistema` (`valores`, `activos`, `cambiar`,
 * `limpiar`); "Limpiar filtros" aparece solo con alguno aplicado.
 */
export default function BarraBusquedaLocal({ id, etiquetaBusqueda, filtros }) {
  const { valores } = filtros;

  return (
    <Row as="form" className="g-2 align-items-end mb-3" role="search" aria-label={t('catalogoSistema.filtros.etiqueta')} onSubmit={(evento) => evento.preventDefault()} noValidate>
      <Col sm={7} lg={5}>
        <CampoFormulario
          id={`${id}-busqueda`}
          etiqueta={etiquetaBusqueda}
          type="search"
          autoComplete="off"
          maxLength={PARAMETROS.limitesCampos.busqueda}
          valor={valores.busqueda}
          onCambiar={(valor) => filtros.cambiar('busqueda', valor)}
          className="mb-0"
        />
      </Col>
      <Col sm={5} lg={3}>
        <CampoSelect
          id={`${id}-estado`}
          etiqueta={t('catalogoSistema.filtros.estado')}
          placeholder={t('catalogoSistema.filtros.todos')}
          opciones={OPCIONES_ESTADO}
          valor={valores.estado}
          onCambiar={(valor) => filtros.cambiar('estado', valor)}
          className="mb-0"
        />
      </Col>
      {filtros.activos && (
        <Col xs="auto">
          <Button variant="outline-secondary" onClick={filtros.limpiar}>{t('comun.limpiarFiltros')}</Button>
        </Col>
      )}
    </Row>
  );
}
