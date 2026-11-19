import { ACCION_FECHA_TURNO_FIJO } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import CampoSelect from './CampoSelect.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const opcionesAccion = () => [
  { valor: ACCION_FECHA_TURNO_FIJO.MANTENER, etiqueta: t('turnosFijos.accionMantener') },
  { valor: ACCION_FECHA_TURNO_FIJO.CANCELAR, etiqueta: t('turnosFijos.accionCancelar') },
];

/**
 * Lleva una fecha concreta de un turno fijo a la agenda (presentación): se elige entre las próximas fechas del turno
 * y qué se hace con ella. Registrarla confirmada permite señarla, completarla o cancelarla desde la agenda; registrarla
 * cancelada libera solo ese día. Una fecha ya registrada responde `409` y el mensaje se muestra en el diálogo.
 */
export default function ModalFechaTurnoFijo({ fecha }) {
  const { turno, opciones, error, enviando } = fecha;

  return (
    <ModalConfirmar
      mostrar={Boolean(turno)}
      titulo={t('turnosFijos.fechaTitulo')}
      textoConfirmar={t('turnosFijos.fechaConfirmar')}
      confirmarDeshabilitado={enviando || !fecha.fecha}
      onConfirmar={fecha.registrar}
      onCancelar={fecha.cerrar}
    >
      {turno && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p className="text-secondary">
            {t('turnosFijos.fechaTexto', { cancha: turno.cancha_nombre, dia: turno.dia_semana_nombre })}
          </p>
          {opciones.length === 0 ? (
            <Alerta variante="warning">{t('turnosFijos.sinFechas')}</Alerta>
          ) : (
            <>
              <CampoSelect
                id="turno-fijo-fecha"
                etiqueta={t('turnosFijos.fecha')}
                valor={fecha.fecha}
                onCambiar={(valor) => fecha.cambiar('fecha', valor)}
                opciones={opciones.map((opcion) => ({ valor: opcion, etiqueta: formatearFechaLarga(opcion) }))}
              />
              <CampoSelect
                id="turno-fijo-accion"
                etiqueta={t('turnosFijos.accion')}
                valor={fecha.accion}
                onCambiar={(valor) => fecha.cambiar('accion', valor)}
                opciones={opcionesAccion()}
                className="mb-0"
              />
            </>
          )}
        </>
      )}
    </ModalConfirmar>
  );
}
