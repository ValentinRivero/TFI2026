import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { describir, ESTADO_RESERVA, opcionesDe, TIPO_OCUPACION } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { estadosSiguientes, puedeCancelarElComplejo, puedeReabrir } from '../utils/agenda.js';
import { formatearFechaCorta, formatearHora } from '../utils/formatos.js';
import { ACCION_COBRO, accionesDeCobro, etiquetaDeEstadoDestino, transferenciaParaRevisar } from '../utils/pagos.js';
import BadgeEstadoReserva from './BadgeEstadoReserva.jsx';
import Icono from './Icono.jsx';
import ResumenPago from './ResumenPago.jsx';
import { CeldaTabla } from './TablaApilable.jsx';

const columnas = 'agenda.columnas';

/**
 * Fila de la agenda: horario, cancha, cliente con su contacto, origen de la reserva, precio y estado de pago, estado,
 * observaciones internas y las acciones que admite el estado actual (cobrar la seña o el total, cambiar estado,
 * rechazar la transferencia informada, anular un cobro si el rol puede, cancelar o reabrir). `ocupada` deshabilita las acciones mientras se aplica un cambio sobre esa reserva.
 */
export default function ReservaAgendaRow({ reserva, ocupada, onCambiarEstado, onCancelar, onReabrir, onCobrar, onEditarObservaciones, onRechazarTransferencia, onAnularCobro, puedeAnularCobro }) {
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
      <CeldaTabla etiqueta={t(`${columnas}.precio`)} className="num"><ResumenPago reserva={reserva} /></CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.estado`)}>
        <BadgeEstadoReserva reserva={reserva} />
        {reserva.conflicto_operatoria && (
          <div className="small text-danger mt-1">{t('agenda.conflicto', { motivo: reserva.conflicto_operatoria })}</div>
        )}
      </CeldaTabla>
      <CeldaTabla etiqueta={t(`${columnas}.observaciones`)}>
        <div className="d-flex align-items-start justify-content-between gap-2">
          <span className="texto-multilinea">{reserva.observaciones || '-'}</span>
          <Button
            size="sm"
            variant="outline-secondary"
            className="boton-icono flex-shrink-0"
            disabled={ocupada}
            title={t('agenda.editarObservaciones')}
            aria-label={t('agenda.editarObservacionesDe', { id: reserva.id })}
            onClick={() => onEditarObservaciones(reserva)}
          >
            <Icono nombre="lapiz" size={16} />
          </Button>
        </div>
      </CeldaTabla>
      <CeldaTabla etiqueta="" className="text-lg-end">
        <div className="d-flex flex-wrap justify-content-lg-end align-items-center gap-2" role="group" aria-label={t('pagos.accionesDe', { id: reserva.id })}>
          {accionesDeCobro(reserva).map((accion) => (
            <Button key={accion} size="sm" variant="outline-primary" disabled={ocupada} onClick={() => onCobrar(reserva, accion)}>
              {t(accion === ACCION_COBRO.SENA ? 'pagos.confirmarSena' : 'pagos.registrarPago')}
            </Button>
          ))}
          {transferenciaParaRevisar(reserva) && (
            <Button size="sm" variant="outline-danger" disabled={ocupada} onClick={() => onRechazarTransferencia(reserva)}>
              {t('transferencia.rechazar')}
            </Button>
          )}
          {puedeAnularCobro && reserva.puede_anular_cobro && (
            <Button size="sm" variant="outline-danger" disabled={ocupada} onClick={() => onAnularCobro(reserva)}>
              {t('pagos.anularCobro')}
            </Button>
          )}
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
              {opcionesDe(ESTADO_RESERVA, siguientes).map(({ valor }) => (
                <option key={valor} value={valor}>{etiquetaDeEstadoDestino(reserva, Number(valor))}</option>
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
