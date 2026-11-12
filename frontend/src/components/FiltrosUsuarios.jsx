import Col from 'react-bootstrap/Col';
import { ESTADO_USUARIO, ETIQUETA_ROL, opcionesDe } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import BarraFiltros from './BarraFiltros.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';

const OPCIONES_ROL = opcionesDe(ETIQUETA_ROL);
const OPCIONES_ESTADO = opcionesDe(ESTADO_USUARIO);

/** Filtros de las cuentas: búsqueda por nombre o correo, rol y estado. `filtros` es lo que devuelve `useFiltrosAplicables`. */
export default function FiltrosUsuarios({ filtros }) {
  const { borrador, cambiar } = filtros;

  return (
    <BarraFiltros etiqueta={t('usuarios.filtros')} onAplicar={filtros.aplicar} onLimpiar={filtros.limpiar}>
      <Col sm={6} lg={3}>
        <CampoFormulario
          id="usuarios-busqueda"
          etiqueta={t('usuarios.buscar')}
          type="search"
          maxLength={PARAMETROS.limitesCampos.busqueda}
          valor={borrador.busqueda}
          onCambiar={(valor) => cambiar('busqueda', valor)}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="usuarios-rol"
          etiqueta={t('usuarios.rol')}
          valor={borrador.rol}
          onCambiar={(valor) => cambiar('rol', valor)}
          placeholder={t('usuarios.todosLosRoles')}
          opciones={OPCIONES_ROL}
          className="mb-0"
        />
      </Col>
      <Col sm={6} lg={3}>
        <CampoSelect
          id="usuarios-estado"
          etiqueta={t('usuarios.estado')}
          valor={borrador.estado}
          onCambiar={(valor) => cambiar('estado', valor)}
          placeholder={t('usuarios.todosLosEstados')}
          opciones={OPCIONES_ESTADO}
          className="mb-0"
        />
      </Col>
    </BarraFiltros>
  );
}
