import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import CampoFormulario from './CampoFormulario.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

const maximo = PARAMETROS.limitesCampos.descripcion;

/**
 * Edición de las observaciones internas de una reserva. `edicion` es lo que devuelve `useEditarObservaciones`: el
 * texto se valida antes de enviar y "Guardar" queda deshabilitado sin cambios o con un texto demasiado largo. Un
 * rechazo del servidor se muestra dentro del diálogo, que queda abierto para corregir o cancelar.
 */
export default function ModalObservaciones({ edicion }) {
  const { reserva, texto, error, errorLocal } = edicion;

  return (
    <ModalConfirmar
      mostrar={Boolean(reserva)}
      titulo={t('agenda.observacionesTitulo')}
      textoConfirmar={t('comun.guardar')}
      confirmarDeshabilitado={!edicion.hayCambios || Boolean(errorLocal) || edicion.enviando}
      onConfirmar={edicion.guardar}
      onCancelar={edicion.cerrar}
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
          <CampoFormulario
            id="reserva-observaciones"
            etiqueta={t('agenda.columnas.observaciones')}
            as="textarea"
            rows={4}
            autoFocus
            valor={texto}
            onCambiar={edicion.cambiar}
            error={errorLocal}
            ayuda={`${t('agenda.ayudaObservaciones')} ${t('agenda.observacionesContador', { usadas: texto.trim().length, maximo })}`}
            className="mb-0"
          />
        </>
      )}
    </ModalConfirmar>
  );
}
