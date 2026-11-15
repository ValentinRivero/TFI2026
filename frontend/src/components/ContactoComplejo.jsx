import useConsulta from '../hooks/useConsulta.js';
import { t } from '../i18n/index.js';
import { obtenerComplejo } from '../services/complejoService.js';

/**
 * Teléfono del complejo para resolver con él lo que ya no se puede hacer desde la aplicación. La reserva no trae el
 * contacto, así que se consulta la ficha pública; si falla o no tiene teléfono, no muestra nada.
 */
export default function ContactoComplejo({ complejoId }) {
  const complejo = useConsulta((signal) => obtenerComplejo(complejoId, signal), [complejoId]);
  const telefono = complejo.datos?.telefono_contacto;
  if (!telefono) return null;

  return (
    <span className="num">
      {t('misReservas.telefonoComplejo')}{' '}
      <a href={`tel:${telefono.replace(/[^\d+]/g, '')}`}>{telefono}</a>
    </span>
  );
}
