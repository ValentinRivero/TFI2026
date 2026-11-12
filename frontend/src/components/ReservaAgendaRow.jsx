import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { describir, ESTADO_RESERVA, opcionesDe, TIPO_OCUPACION } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { estadosSiguientes, puedeCancelarElComplejo, puedeReabrir } from '../utils/agenda.js';
import { formatearFechaCorta, formatearHora, formatearPrecio } from '../utils/formatos.js';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'agenda.columnas';

/**
 * Fila de la agenda: horario, cancha, cliente con su contacto, origen de la reserva, precio acordado, estado,
 * observaciones internas y las acciones que admite el estado actual (cambiar estado, cancelar o reabrir).
 * `ocupada` deshabilita las acciones mientras se aplica un cambio sobre esa reserva.
 */
export default function ReservaAgendaRow({ reserva, ocupada, onCambiarEstado, onCancelar, onReabrir }) {
  const { etiqueta, badge } = describir(ESTADO_RESERVA, reserva.estado);
  const origen = describir(TIPO_OCUPACION, reserva.tipo_ocupacion);
  const siguientes = estadosSiguientes(reserva);
  const { cliente } = reserva;

  return (
    <tr>
      <CeldaTabla etiqueta={t(`${columnas}.horario`)} className="num">
        <div>{formatearFechaCorta(reserva.fecha_turno)}</div>
        <div>{t('grilla.resumenHorarioValor', { inicio: formatearHora(reserva.hora_inicio), fin: formatearHora(reserva.hora_fin) })}</div>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.cancha`)}>{reserva.cancha_nombre}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.cliente`)}>
        <div>{cliente.nombre || '-'}</div>
        {cliente.telefono && <div className="small text-secondary num">{cliente.telefono}</div>}
        {cliente.email && <div className="small text-secondary">{cliente.email}</div>}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.origen`)}>
        <span className={`badge ${origen.badge}`}>{origen.etiqueta}</span>
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.precio`)} className="num">{formatearPrecio(reserva.precio_acordado)}</CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <span className={`badge ${badge}`}>{etiqueta}</span>
        {reserva.conflicto_operatoria && (
          <div className="small text-danger mt-1">{t('agenda.conflicto', { motivo: reserva.conflicto_operatoria })}</div>
        )}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.observaciones`)} className="texto-multilinea">{reserva.observaciones || '-'}</CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <div className="d-flex flex-wrap justify-content-lg-end align-items-center gap-2">
          {siguientes.length > 0 && (
            <Form.Select
              size="sm"
              value=""
              disabled={ocupada}
              aria-label={t('agenda.cambiarEstadoDe', { id: reserva.id })}
              onChange={(evento) => onCambiarEstado(reserva, Number(evento.target.value))}
              className="agenda-cambio-estado"
            >
              <option value="">{t('agenda.cambiarEstado')}</option>
              {opcionesDe(ESTADO_RESERVA, siguientes).map(({ valor, etiqueta: texto }) => (
                <option key={valor} value={valor}>{texto}</option>
              ))}
            </Form.Select>
          )}
          {puedeCancelarElComplejo(reserva) && (
            <Button size="sm" variant="outline-danger" disabled={ocupada} onClick={() => onCancelar(reserva)}>
              {t('agenda.cancelar')}
            </Button>
          )}
          {puedeReabrir(reserva) && (
            <Button size="sm" variant="outline-primary" disabled={ocupada} onClick={() => onReabrir(reserva)}>
              {t('agenda.reabrir')}
            </Button>
          )}
        </div>
      </CeldaTabla>
    </tr>
  );
}
