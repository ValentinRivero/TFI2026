import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import ConfirmarConflicto from './ConfirmarConflicto.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';
import SelectorBloquesHorarios from './SelectorBloquesHorarios.jsx';
import VistaPreviaCambio from './VistaPreviaCambio.jsx';

/**
 * Edición de un turno fijo (presentación): el horario de inicio (el fin se recalcula) y el fin de la vigencia. La
 * cancha, el día y el inicio de la vigencia no se editan. Un cambio de horario pide confirmación: el servidor responde
 * `409` con una vista previa y `ConfirmarConflicto` la muestra antes de aplicar. `edicion` es lo que devuelve
 * `useTurnosFijos`.
 */
export default function ModalEditarTurnoFijo({ edicion }) {
  const { turno, conflicto, error, enviando } = edicion;

  return (
    <>
      <ModalConfirmar
        mostrar={Boolean(turno) && !conflicto}
        titulo={t('turnosFijos.editarTitulo')}
        textoConfirmar={t('comun.guardar')}
        confirmarDeshabilitado={enviando}
        onConfirmar={edicion.guardar}
        onCancelar={edicion.cerrar}
      >
        {turno && (
          <>
            {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
            <p className="text-secondary">
              {t('turnosFijos.editarTexto', { cancha: turno.cancha_nombre, dia: turno.dia_semana_nombre })}
            </p>
            <div className="mb-3">
              <SelectorBloquesHorarios
                bloques={edicion.bloques}
                valor={edicion.hora_inicio}
                onElegir={(hora) => edicion.cambiar('hora_inicio', hora)}
                error={error?.campos?.hora_inicio}
              />
              <p className="small text-secondary mt-1 mb-0">{t('turnosFijos.ayudaHoraEdicion')}</p>
            </div>
            <CampoFormulario
              id="turno-fijo-editar-fin"
              etiqueta={t('turnosFijos.vigenciaHasta')}
              type="date"
              min={turno.fecha_inicio_vigencia}
              valor={edicion.fecha_fin_vigencia}
              onCambiar={(valor) => edicion.cambiar('fecha_fin_vigencia', valor)}
              error={error?.campos?.fecha_fin_vigencia}
              ayuda={t('turnosFijos.ayudaSinFin')}
              className="mb-0"
            />
          </>
        )}
      </ModalConfirmar>

      <ConfirmarConflicto
        conflicto={conflicto}
        error={error}
        titulo={t('turnosFijos.cambioHorarioTitulo')}
        textoConfirmar={t('turnosFijos.cambioHorarioConfirmar')}
        aclaracion={t('turnosFijos.cambioHorarioAclaracion')}
        mostrarMensaje={false}
        onConfirmar={edicion.confirmar}
        onCancelar={edicion.volver}
      >
        <VistaPreviaCambio vistaPrevia={conflicto?.vistaPrevia} />
      </ConfirmarConflicto>
    </>
  );
}
