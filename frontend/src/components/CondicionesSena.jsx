import { t } from '../i18n/index.js';
import { exigeSena } from '../utils/pagos.js';

/**
 * Condiciones de seña del complejo para quien reserva: el porcentaje que exige (o que no exige seña) y el texto libre
 * con los detalles. Lo comparten la ficha del complejo y la confirmación de la reserva.
 */
export default function CondicionesSena({ complejo }) {
  const { porcentaje_sena: porcentaje, info_sena: informacion } = complejo;
  return (
    <>
      <span className="d-block">
        {exigeSena(complejo) ? t('complejo.senaPorcentaje', { porcentaje }) : t('complejo.sinSena')}
      </span>
      {informacion && <span className="d-block texto-multilinea">{informacion}</span>}
    </>
  );
}
