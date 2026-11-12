import { BLOQUE_LIBRE, ESTADO_BLOQUE } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearHora, formatearPrecio } from '../utils/formatos.js';
import Icono from './Icono.jsx';

// Qué se escribe bajo la hora según el estado del bloque: el precio si está libre y el motivo si lo cierra una excepción.
const detalleDe = (bloque) => {
  if (bloque.estado === BLOQUE_LIBRE) return formatearPrecio(bloque.precio);
  const etiqueta = ESTADO_BLOQUE[bloque.estado]?.etiqueta ?? ESTADO_BLOQUE.NO_DISPONIBLE.etiqueta;
  return bloque.estado === 'CERRADO_EXCEPCION' && bloque.motivo ? bloque.motivo : etiqueta;
};

/**
 * Un bloque horario de la grilla con sus cinco estados visuales: libre, ocupado, cerrado por excepción, no
 * disponible (los cuatro que informa el backend) y seleccionado (la elección del cliente sobre un bloque libre).
 * Solo el libre y el seleccionado se pueden pulsar.
 */
export default function CasilleroGrilla({ bloque, seleccionado = false, onElegir }) {
  const libre = bloque.estado === BLOQUE_LIBRE;
  const variante = seleccionado ? 'seleccionado' : (ESTADO_BLOQUE[bloque.estado]?.casillero ?? 'no-disponible');
  const hora = formatearHora(bloque.hora_inicio);
  const detalle = detalleDe(bloque);

  return (
    <button
      type="button"
      className={`casillero casillero-${variante}`}
      disabled={!libre}
      aria-pressed={libre ? seleccionado : undefined}
      aria-label={t('grilla.etiquetaCasillero', {
        hora,
        estado: seleccionado ? `${detalle}, ${t('grilla.seleccionado')}` : detalle,
      })}
      title={`${hora} - ${formatearHora(bloque.hora_fin)}`}
      onClick={() => onElegir?.(bloque)}
    >
      <span className="casillero__hora num">
        <span className="casillero__marca me-1"><Icono nombre="check" tamano={14} /></span>
        {hora}
      </span>
      <span className="casillero__detalle">{detalle}</span>
    </button>
  );
}
