import Button from 'react-bootstrap/Button';
import Alerta from '../components/Alerta.jsx';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import FiltrosContratos from '../components/FiltrosContratos.jsx';
import FormularioComplejoNuevo from '../components/FormularioComplejoNuevo.jsx';
import ModalEstadoContrato from '../components/ModalEstadoContrato.jsx';
import TablaContratos from '../components/TablaContratos.jsx';
import useContratos from '../hooks/useContratos.js';
import { t } from '../i18n/index.js';

/**
 * Contratos de los complejos (superadmin): alta de un complejo con su propietario, listado con filtros y cambio de
 * estado del contrato. Un contrato suspendido o dado de baja oculta el complejo del catálogo público.
 */
export default function Contratos() {
  const contratos = useContratos();
  const { alta } = contratos;

  return (
    <div>
      <EncabezadoPantalla titulo={t('contratos.titulo')} descripcion={t('contratos.descripcion')} />
      {contratos.aviso && <Alerta variante="success" onCerrar={contratos.descartarAviso}>{contratos.aviso}</Alerta>}

      {alta.abierta ? (
        <FormularioComplejoNuevo formulario={alta} />
      ) : (
        <div className="mb-3">
          <Button onClick={alta.abrir}>{t('contratos.nuevo')}</Button>
        </div>
      )}

      <FiltrosContratos filtros={contratos.filtros} />
      <TablaContratos lista={contratos.lista} onCambiarEstado={contratos.cambio.pedir} />
      <ModalEstadoContrato cambio={contratos.cambio} />
    </div>
  );
}
