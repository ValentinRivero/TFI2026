import { ESTADO_CONTRATO, opcionesDe } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import CampoSelect from './CampoSelect.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const OPCIONES = opcionesDe(ESTADO_CONTRATO);

/**
 * Cambio de estado del contrato de un complejo (presentación). Suspendido o baja ocultan el complejo del catálogo sin
 * tocar canchas ni reservas; activarlo exige un dueño activo y, si no, el backend lo rechaza y el motivo se muestra
 * acá. `cambio` es lo que devuelve `useContratos`.
 */
export default function ModalEstadoContrato({ cambio }) {
  const { contrato, estado, error, enviando } = cambio;

  return (
    <ModalConfirmar
      mostrar={Boolean(contrato)}
      titulo={t('contratos.estadoTitulo')}
      textoConfirmar={t('comun.guardar')}
      confirmarDeshabilitado={enviando}
      onConfirmar={cambio.guardar}
      onCancelar={cambio.cerrar}
    >
      {contrato && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p>{t('contratos.estadoTexto', { nombre: contrato.nombre })}</p>
          <CampoSelect
            id="contrato-estado"
            etiqueta={t('contratos.estado')}
            valor={estado}
            onCambiar={cambio.cambiarEstado}
            opciones={OPCIONES}
            error={error?.campos?.estado_contrato}
            ayuda={t('contratos.estadoAyuda')}
            className="mb-0"
          />
        </>
      )}
    </ModalConfirmar>
  );
}
