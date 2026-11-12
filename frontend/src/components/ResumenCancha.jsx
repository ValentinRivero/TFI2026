import { t } from '../i18n/index.js';
import { describirCancha } from '../utils/cancha.js';
import { formatearPrecio } from '../utils/formatos.js';

/** Resumen de una línea de la cancha elegida: superficie, cobertura, iluminación y precio base. */
export default function ResumenCancha({ cancha }) {
  const { superficie, cobertura, iluminacion } = describirCancha(cancha);

  return (
    <p className="text-secondary mb-0">
      {[superficie, cobertura, iluminacion].filter(Boolean).join(' · ')}
      {' · '}
      <span className="num">{formatearPrecio(cancha.precio_base)}</span> {t('cancha.porTurno')}
    </p>
  );
}
