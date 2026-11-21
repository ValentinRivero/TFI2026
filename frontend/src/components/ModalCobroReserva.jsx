import { t } from '../i18n/index.js';
import { formatearFechaLarga, formatearHora, formatearPrecio } from '../utils/formatos.js';
import { ACCION_COBRO } from '../utils/pagos.js';
import Alerta from './Alerta.jsx';
import ModalConfirmar from './ModalConfirmar.jsx';

/**
 * Confirmación de un cobro desde la agenda: recibir la seña o registrar el pago total. `cobro` viene de
 * `useConfirmacion`: su `objetivo` es `{ reserva, accion }`. Un rechazo del servidor (reserva ya señada, cancelada o
 * saldada) se muestra dentro del diálogo, que queda abierto para cancelar.
 */
export default function ModalCobroReserva({ cobro }) {
  const { objetivo, error } = cobro;
  if (!objetivo) return null;
  const { reserva, accion } = objetivo;
  const esSena = accion === ACCION_COBRO.SENA;
  const monto = esSena ? Number(reserva.monto_sena) - Number(reserva.monto_pagado) : reserva.saldo_restante;

  return (
    <ModalConfirmar
      mostrar
      titulo={t(esSena ? 'pagos.confirmarSenaTitulo' : 'pagos.registrarPagoTitulo')}
      textoConfirmar={t(esSena ? 'pagos.confirmarSena' : 'pagos.registrarPago')}
      onConfirmar={cobro.confirmar}
      onCancelar={cobro.cerrar}
    >
      {error && <Alerta variante="danger">{error.mensaje}</Alerta>}
      <p className="mb-0">
        {t(esSena ? 'pagos.confirmarSenaTexto' : 'pagos.registrarPagoTexto', {
          monto: formatearPrecio(monto),
          fecha: formatearFechaLarga(reserva.fecha_turno),
          hora: formatearHora(reserva.hora_inicio),
          cancha: reserva.cancha_nombre,
        })}
      </p>
    </ModalConfirmar>
  );
}
