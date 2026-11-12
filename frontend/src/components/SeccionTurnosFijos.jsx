import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import BandejaFechasEnEspera from './BandejaFechasEnEspera.jsx';
import FiltrosTurnosFijos from './FiltrosTurnosFijos.jsx';
import FormularioTurnoFijo from './FormularioTurnoFijo.jsx';
import ModalConfirmarAccion from './ModalConfirmarAccion.jsx';
import ModalEditarTurnoFijo from './ModalEditarTurnoFijo.jsx';
import ModalFechaTurnoFijo from './ModalFechaTurnoFijo.jsx';
import TablaTurnosFijos from './TablaTurnosFijos.jsx';

/**
 * Pestaña "Turnos fijos" de la agenda (presentación): bandeja de fechas en espera por excepción, alta, filtros, tabla
 * paginada y los diálogos de edición, registro de fechas y baja. `turnos` es lo que devuelve `useTurnosFijos`.
 */
export default function SeccionTurnosFijos({ turnos, canchas }) {
  const { alta, baja } = turnos;

  return (
    <div>
      {turnos.aviso && <Alerta variante="success" onCerrar={turnos.descartarAviso}>{turnos.aviso}</Alerta>}
      {turnos.errorAccion && <Alerta variante="danger" onCerrar={turnos.descartarError}>{turnos.errorAccion.mensaje}</Alerta>}

      <BandejaFechasEnEspera espera={turnos.enEspera} />

      {alta.abierta ? (
        <FormularioTurnoFijo formulario={alta} canchas={canchas} />
      ) : (
        <div className="mb-3">
          <Button onClick={alta.abrir}>{t('turnosFijos.nuevo')}</Button>
        </div>
      )}

      <FiltrosTurnosFijos
        filtros={turnos.filtros}
        canchas={canchas}
        onCambiar={turnos.cambiarFiltro}
        onLimpiar={turnos.limpiarFiltros}
      />
      <TablaTurnosFijos
        lista={turnos.lista}
        cambiando={turnos.cambiando}
        onEditar={turnos.edicion.pedir}
        onRegistrarFechas={turnos.fecha.pedir}
        onAlternarPausa={turnos.alternarPausa}
        onBaja={baja.pedir}
      />

      <ModalEditarTurnoFijo edicion={turnos.edicion} />
      <ModalFechaTurnoFijo fecha={turnos.fecha} />
      <ModalConfirmarAccion
        abierto={Boolean(baja.objetivo)}
        titulo={t('turnosFijos.bajaTitulo')}
        texto={t('turnosFijos.bajaTexto')}
        error={baja.error}
        textoConfirmar={t('turnosFijos.darDeBaja')}
        onConfirmar={baja.confirmar}
        onCancelar={baja.cerrar}
      />
    </div>
  );
}
