import { t } from '../i18n/index.js';
import { formatearEntero, formatearPorcentaje } from '../utils/formatos.js';
import { anchoDeBarra } from '../utils/reportes.js';
import EstadoVacio from './EstadoVacio.jsx';
import ListaBarras from './ListaBarras.jsx';
import TarjetaReporte from './TarjetaReporte.jsx';

const PORCENTAJE_COMPLETO = 100;

/**
 * Porcentaje de ocupación por cancha: minutos ocupados sobre los que ofrecía la grilla. `ocupacion` es `null` cuando el
 * criterio de fecha no es el día de juego (el rango no describe días de juego) y una cancha sin oferta figura sin porcentaje.
 */
export default function OcupacionCanchas({ ocupacion }) {
  return (
    <TarjetaReporte titulo={t('reportes.ocupacion')} descripcion={t('reportes.ocupacionDescripcion')}>
      {ocupacion === null && <p className="text-secondary mb-0">{t('reportes.ocupacionNoAplica')}</p>}
      {ocupacion !== null && ocupacion.length === 0 && (
        <EstadoVacio titulo={t('reportes.ocupacionVacia')} className="border-0 p-0 text-start" />
      )}
      {ocupacion !== null && ocupacion.length > 0 && (
        <ListaBarras
          etiqueta={t('reportes.ocupacion')}
          filas={ocupacion.map((cancha) => ({
            clave: cancha.cancha_id,
            etiqueta: cancha.cancha,
            valor: cancha.porcentaje === null
              ? t('reportes.sinOferta')
              : t('reportes.ocupacionValor', {
                porcentaje: formatearPorcentaje(cancha.porcentaje),
                ocupados: formatearEntero(cancha.minutos_ocupados),
                ofertables: formatearEntero(cancha.minutos_ofertables),
              }),
            ancho: anchoDeBarra(cancha.porcentaje, PORCENTAJE_COMPLETO),
            variante: 'info',
          }))}
        />
      )}
    </TarjetaReporte>
  );
}
