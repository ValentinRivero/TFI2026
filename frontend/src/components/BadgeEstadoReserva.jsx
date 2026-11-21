import { estadoDeReserva } from '../utils/pagos.js';

/**
 * Estado de una reserva como badge del tema. Una señada muestra su estado de pago (seña abonada o pagada) y una
 * pendiente sin seña se llama «Pendiente»: ver `estadoDeReserva`.
 */
export default function BadgeEstadoReserva({ reserva }) {
  const { etiqueta, badge } = estadoDeReserva(reserva);
  return <span className={`badge ${badge}`}>{etiqueta}</span>;
}
