import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import ConfirmarConflicto from './ConfirmarConflicto.jsx';
import FiltrosAgenda from './FiltrosAgenda.jsx';
import FormularioReservaManual from './FormularioReservaManual.jsx';
import ModalCobroReserva from './ModalCobroReserva.jsx';
import ModalConfirmarAccion from './ModalConfirmarAccion.jsx';
import ModalObservaciones from './ModalObservaciones.jsx';
import ModalReabrirReserva from './ModalReabrirReserva.jsx';
import TablaAgenda from './TablaAgenda.jsx';
import VistaPreviaCambio from './VistaPreviaCambio.jsx';

/**
 * Pestaña "Reservas" de la agenda (presentación): avisos, alta manual, filtros, tabla paginada y los diálogos
 * de cobro, observaciones, cancelación y reapertura. `agenda` es lo que devuelve `useAgenda` y `canchas`, `[{ id, nombre }]` del complejo.
 */
export default function SeccionReservasAgenda({ agenda, canchas }) {
  const { alta, cancelacion, cobro, observaciones, reapertura } = agenda;
  const reserva = cancelacion.objetivo;

  return (
    <div>
      {agenda.aviso && <Alerta variante="success" onCerrar={agenda.descartarAviso}>{agenda.aviso}</Alerta>}
      {agenda.errorAccion && <Alerta variante="danger" onCerrar={agenda.descartarError}>{agenda.errorAccion.mensaje}</Alerta>}

      {alta.abierta ? (
        <FormularioReservaManual formulario={alta} canchas={canchas} />
      ) : (
        <div className="mb-3">
          <Button onClick={alta.abrir}>{t('agenda.registrarManual')}</Button>
        </div>
      )}

      <FiltrosAgenda
        filtros={agenda.filtros}
        errores={agenda.erroresFiltros}
        periodo={agenda.periodo}
        canchas={canchas}
        onCambiar={agenda.cambiarFiltro}
        onAlternarRango={agenda.alternarRango}
        onElegirPeriodo={agenda.elegirPeriodo}
        onLimpiar={agenda.limpiarFiltros}
      />
      <TablaAgenda
        lista={agenda.lista}
        cambiando={agenda.cambiando}
        onCambiarEstado={agenda.cambiarEstado}
        onCancelar={cancelacion.pedir}
        onReabrir={reapertura.pedir}
        onCobrar={(reserva, accion) => cobro.pedir({ reserva, accion })}
        onEditarObservaciones={observaciones.abrir}
      />

      <ModalObservaciones edicion={observaciones} />

      <ModalCobroReserva cobro={cobro} />

      <ModalConfirmarAccion
        abierto={Boolean(reserva)}
        titulo={t('agenda.cancelarTitulo')}
        texto={reserva ? t('agenda.cancelarTexto', {
          fecha: formatearFechaLarga(reserva.fecha_turno),
          hora: formatearHora(reserva.hora_inicio),
          cancha: reserva.cancha_nombre,
        }) : ''}
        error={cancelacion.error}
        textoConfirmar={t('agenda.cancelarConfirmar')}
        onConfirmar={cancelacion.confirmar}
        onCancelar={cancelacion.cerrar}
      />

      <ModalReabrirReserva reapertura={reapertura} />
      <ConfirmarConflicto
        conflicto={reapertura.conflicto}
        error={reapertura.error}
        titulo={t('agenda.reabrirConfirmarTitulo')}
        textoConfirmar={t('agenda.reabrirConfirmar')}
        aclaracion={t('agenda.reabrirAclaracion')}
        mostrarMensaje={false}
        onConfirmar={reapertura.confirmar}
        onCancelar={reapertura.cerrar}
      >
        <VistaPreviaCambio vistaPrevia={reapertura.conflicto?.vistaPrevia} />
      </ConfirmarConflicto>
    </div>
  );
}
