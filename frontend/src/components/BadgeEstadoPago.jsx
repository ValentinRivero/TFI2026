import { estadoDePago } from '../utils/pagos.js';

/** Estado de pago de una reserva (sin seña, seña pendiente o abonada, pagada) como badge del tema. */
export default function BadgeEstadoPago({ reserva }) {
  const { etiqueta, badge } = estadoDePago(reserva);
  return <span className={`badge ${badge}`}>{etiqueta}</span>;
}
