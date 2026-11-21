import { ESTADO_RESERVA, opcionesDe } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { estadosDeReapertura } from '../utils/agenda.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import CampoSelect from './CampoSelect.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Primer paso de la reapertura de una reserva cancelada: elegir el estado con el que vuelve a ocupar su turno. Al
 * continuar, el servidor revalida el turno; si sigue libre, la confirmación final la muestra `ConfirmarConflicto`.
 * `reapertura` es lo que devuelve `useAgenda`.
 */
export default function ModalReabrirReserva({ reapertura }) {
  const { reserva, estado, error, enviando } = reapertura;

  return (
    <ModalConfirmar
      mostrar={Boolean(reserva) && !reapertura.conflicto}
      titulo={t('agenda.reabrirTitulo')}
      textoConfirmar={t('agenda.reabrirContinuar')}
      confirmarDeshabilitado={enviando}
      onConfirmar={reapertura.continuar}
      onCancelar={reapertura.cerrar}
    >
      {reserva && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p>
            {t('agenda.reabrirTexto', {
              fecha: formatearFechaLarga(reserva.fecha_turno),
              hora: formatearHora(reserva.hora_inicio),
              cancha: reserva.cancha_nombre,
            })}
          </p>
          <CampoSelect
            id="reabrir-estado"
            etiqueta={t('agenda.reabrirEstado')}
            valor={estado}
            onCambiar={reapertura.cambiarEstado}
            opciones={opcionesDe(ESTADO_RESERVA, estadosDeReapertura(reserva))}
            className="mb-0"
          />
        </>
      )}
    </ModalConfirmar>
  );
}
