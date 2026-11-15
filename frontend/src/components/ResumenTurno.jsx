import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import AvisoSinCancelacion from './AvisoSinCancelacion.jsx';
import DatosTurno from './DatosTurno.jsx';

/**
 * Resumen del turno elegido en la grilla. `onReservar` abre el flujo de reserva: sin él, el botón se muestra
 * deshabilitado y `nota` explica por qué. `horasSinCancelacion` (si el turno ya está dentro del margen de cancelación
 * del complejo) muestra la advertencia antes de reservar. `children` es el lugar del pronóstico del día.
 */
export default function ResumenTurno({ cancha, bloque, fecha, onReservar, onQuitar, nota, horasSinCancelacion, children }) {
  return (
    <section className="superficie p-3" aria-labelledby="resumen-turno-titulo" aria-live="polite">
      <h3 id="resumen-turno-titulo" className="h5">{t('grilla.resumenTitulo')}</h3>
      <DatosTurno cancha={cancha} bloque={bloque} fecha={fecha} />
      {children && <div className="mb-3">{children}</div>}
      {horasSinCancelacion && <AvisoSinCancelacion horas={horasSinCancelacion} className="mb-3" />}
      {nota && <p className="small text-secondary">{nota}</p>}
      <div className="d-flex flex-wrap gap-2">
        <Button variant="primary" disabled={!onReservar} onClick={onReservar}>{t('grilla.reservar')}</Button>
        <Button variant="outline-secondary" onClick={onQuitar}>{t('grilla.quitar')}</Button>
      </div>
    </section>
  );
}
