import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { t } from '../i18n/index.js';
import { formatearFechaLarga, parsearFecha, sumarDias } from '../utils/formatos.js';
import Icono from './Icono.jsx';

/**
 * Selector del día de la grilla: día anterior, calendario (mínimo `hoy`) y día siguiente. `children` es el lugar
 * del pronóstico del día elegido. Solo avisa fechas válidas y no anteriores a hoy.
 */
export default function SelectorFechaGrilla({ fecha, hoy, onCambiar, children }) {
  const cambiar = (nueva) => {
    if (nueva && parsearFecha(nueva) && nueva >= hoy) onCambiar(nueva);
  };

  return (
    <div className="mb-3">
      <div className="d-flex flex-wrap align-items-end gap-2">
        <Button variant="outline-secondary" aria-label={t('grilla.diaAnterior')} disabled={fecha <= hoy} onClick={() => cambiar(sumarDias(fecha, -1))}>
          <Icono nombre="anterior" tamano={18} />
        </Button>
        <Form.Group controlId="grilla-fecha">
          <Form.Label className="visually-hidden">{t('grilla.fecha')}</Form.Label>
          <Form.Control type="date" value={fecha} min={hoy} onChange={(evento) => cambiar(evento.target.value)} />
        </Form.Group>
        <Button variant="outline-secondary" aria-label={t('grilla.diaSiguiente')} onClick={() => cambiar(sumarDias(fecha, 1))}>
          <Icono nombre="siguiente" tamano={18} />
        </Button>
        <span className="text-capitalize fw-semibold align-self-center ms-1">{formatearFechaLarga(fecha)}</span>
      </div>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}
