import Col from 'react-bootstrap/Col';
import { ESTADO_CONTRATO, opcionesDe, ORDENES_CONTRATO } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import BarraFiltros from './BarraFiltros.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_ESTADO = opcionesDe(ESTADO_CONTRATO);

/** Filtros de los contratos: estado, búsqueda por nombre y orden. `filtros` es lo que devuelve `useFiltrosAplicables`. */
export default function FiltrosContratos({ filtros }) {
  const { borrador, cambiar } = filtros;

  return (
    <BarraFiltros etiqueta={t('contratos.filtros')} onAplicar={filtros.aplicar} onLimpiar={filtros.limpiar}>
      <Col sm={6} lg={3}>
        <CampoFormulario
          id="contratos-busqueda"
          etiqueta={t('contratos.buscar')}
          type="search"
          maxLength={PARAMETROS.limitesCampos.busqueda}
          valor={borrador.busqueda}
          onCambiar={(valor) => cambiar('busqueda', valor)}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="contratos-estado"
          etiqueta={t('contratos.estado')}
          valor={borrador.estado}
          onCambiar={(valor) => cambiar('estado', valor)}
          placeholder={t('contratos.todosLosEstados')}
          opciones={OPCIONES_ESTADO}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="contratos-orden"
          etiqueta={t('contratos.orden')}
          valor={borrador.orden}
          onCambiar={(valor) => cambiar('orden', valor)}
          opciones={ORDENES_CONTRATO.map(({ valor, clave }) => ({ valor, etiqueta: t(clave) }))}
          className="mb-0"
        />
      </Col>
    </BarraFiltros>
  );
}
