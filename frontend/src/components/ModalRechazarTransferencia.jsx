import { MOTIVO_RECHAZO_TRANSFERENCIA, opcionesDe } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import CampoSelect from './CampoSelect.jsx';
import DatosTransferenciaInformada from './DatosTransferenciaInformada.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const OPCIONES = opcionesDe(MOTIVO_RECHAZO_TRANSFERENCIA);

/**
 * Rechazo de la transferencia informada por el jugador. `formulario` es lo que devuelve `useRechazarTransferencia`.
 * Muestra lo que se informó para tenerlo a la vista, pide un motivo de la lista y una nota opcional, y aclara que el
 * jugador recibe un aviso y puede volver a informarla (o el personal confirmar la seña igual).
 */
export default function ModalRechazarTransferencia({ formulario }) {
  const { reserva, error } = formulario;

  return (
    <ModalConfirmar
      mostrar={Boolean(reserva)}
      titulo={t('transferencia.rechazarTitulo')}
      textoConfirmar={t('transferencia.rechazar')}
      variante="danger"
      confirmarDeshabilitado={Boolean(formulario.errorNota) || formulario.enviando}
      onConfirmar={formulario.guardar}
      onCancelar={formulario.cerrar}
    >
      {reserva && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p className="small text-secondary">
            {t('agenda.observacionesTurno', {
              fecha: formatearFechaLarga(reserva.fecha_turno),
              hora: formatearHora(reserva.hora_inicio),
              cancha: reserva.cancha_nombre,
            })}
          </p>
          <section className="superficie p-3 mb-3" aria-label={t('transferencia.datosInformados')}>
            <h3 className="h6">{t('transferencia.datosInformados')}</h3>
            <DatosTransferenciaInformada transferencia={reserva.transferencia} />
          </section>
          <CampoSelect
            id="rechazo-motivo"
            etiqueta={t('transferencia.motivo')}
            valor={formulario.motivo}
            onCambiar={(valor) => formulario.cambiar('motivo', valor)}
            opciones={OPCIONES}
          />
          <CampoFormulario
            id="rechazo-nota"
            etiqueta={t('transferencia.nota')}
            as="textarea"
            rows={2}
            maxLength={PARAMETROS.pagos.notaRechazoMaximo}
            valor={formulario.nota}
            onCambiar={(valor) => formulario.cambiar('nota', valor)}
            error={formulario.errorNota}
            ayuda={t('transferencia.ayudaNota')}
            className="mb-2"
          />
          <p className="small text-secondary mb-0">{t('transferencia.avisoRechazo')}</p>
        </>
      )}
    </ModalConfirmar>
  );
}
