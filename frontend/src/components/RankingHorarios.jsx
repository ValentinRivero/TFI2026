import { t } from '../i18n/index.js';
import { formatearEntero, formatearHora } from '../utils/formatos.js';
import { anchoDeBarra, maximoDe } from '../utils/reportes.js';
import EstadoVacio from './EstadoVacio.jsx';
import ListaBarras from './ListaBarras.jsx';
import TarjetaReporte from './TarjetaReporte.jsx';

/** Horarios de inicio con más reservas del rango, de mayor a menor. `ranking` es `[{ hora_inicio, reservas }]`. */
export default function RankingHorarios({ ranking }) {
  const mayor = maximoDe(ranking, 'reservas');

  return (
    <TarjetaReporte titulo={t('reportes.ranking')} descripcion={t('reportes.rankingDescripcion')}>
      {ranking.length === 0 ? (
        <EstadoVacio titulo={t('reportes.rankingVacio')} className="border-0 p-0 text-start" />
      ) : (
        <ListaBarras
          etiqueta={t('reportes.ranking')}
          filas={ranking.map((horario) => ({
            clave: horario.hora_inicio,
            etiqueta: formatearHora(horario.hora_inicio),
            valor: t('reportes.reservasValor', { cantidad: formatearEntero(horario.reservas) }),
            ancho: anchoDeBarra(horario.reservas, mayor),
            variante: 'ok',
          }))}
        />
      )}
    </TarjetaReporte>
  );
}
