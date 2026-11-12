import { DIA_SEMANA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora } from '../utils/formatos.js';
import Alerta from './Alerta.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Confirmación de un cambio que deja reservas o turnos fijos fuera de la grilla (`409` con `requiere_confirmacion`).
 * Detalla qué queda afectado y avisa que nada se cancela solo. `conflicto` es el resultado de `leerConflictos`
 * (`null` mantiene el diálogo cerrado); `error` es el de un reintento fallido. Lo usan los cambios de cancha y de
 * horarios, y lo reutilizan los turnos fijos.
 */
export default function ConfirmarConflicto({ conflicto, error, onConfirmar, onCancelar }) {
  return (
    <ModalConfirmar
      mostrar={Boolean(conflicto)}
      titulo={t('conflicto.titulo')}
      textoConfirmar={t('conflicto.aplicar')}
      textoCancelar={t('conflicto.noAplicar')}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
    >
      {conflicto && (
        <>
          {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
          <p>{conflicto.mensaje}</p>

          {conflicto.reservas.length > 0 && (
            <section className="mb-3">
              <h3 className="h6">{t('conflicto.reservas', { cantidad: conflicto.reservas.length })}</h3>
              <ul className="mb-0">
                {conflicto.reservas.map((reserva) => (
                  <li key={reserva.id}>
                    <span className="num">
                      {t('conflicto.reserva', {
                        id: reserva.id,
                        fecha: formatearFechaLarga(reserva.fecha_turno),
                        hora: formatearHora(reserva.hora_inicio),
                      })}
                    </span>
                    {reserva.motivo && <span className="text-secondary"> - {reserva.motivo}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {conflicto.turnosFijos.length > 0 && (
            <section className="mb-3">
              <h3 className="h6">{t('conflicto.turnosFijos', { cantidad: conflicto.turnosFijos.length })}</h3>
              <ul className="mb-0">
                {conflicto.turnosFijos.map((turno) => (
                  <li key={turno.id}>
                    <span className="num">
                      {t('conflicto.turnoFijo', {
                        id: turno.id,
                        dia: DIA_SEMANA[turno.dia_semana]?.etiqueta ?? turno.dia_semana,
                        hora: formatearHora(turno.hora_inicio),
                      })}
                    </span>
                    {turno.motivo && <span className="text-secondary"> - {turno.motivo}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <p className="small text-secondary mb-0">{t('conflicto.aclaracion')}</p>
        </>
      )}
    </ModalConfirmar>
  );
}
