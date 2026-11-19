import { describir, ESTADO_RESERVA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { formatearEntero } from '../utils/formatos.js';
import { anchoDeBarra, filasDeConteo, maximoDe } from '../utils/reportes.js';
import ListaBarras from './ListaBarras.jsx';
import TarjetaReporte from './TarjetaReporte.jsx';

// Variante de la barra según la clase de badge del estado (`badge-ok` -> `ok`), para que cada estado conserve su color.
const varianteDe = (badge) => badge.replace('badge-', '');

/** Cantidad de reservas por estado del rango, como barras proporcionales a la mayor. `conteos` es el del dashboard. */
export default function DesgloseEstados({ conteos }) {
  const filas = filasDeConteo(conteos);
  const mayor = maximoDe(filas, 'cantidad');

  return (
    <TarjetaReporte titulo={t('reportes.desglose')} descripcion={t('reportes.desgloseDescripcion')}>
      <ListaBarras
        etiqueta={t('reportes.desglose')}
        filas={filas.map(({ clave, estado, cantidad }) => {
          const { etiqueta, badge } = describir(ESTADO_RESERVA, estado);
          return {
            clave,
            etiqueta,
            valor: formatearEntero(cantidad),
            ancho: anchoDeBarra(cantidad, mayor),
            variante: varianteDe(badge),
          };
        })}
      />
    </TarjetaReporte>
  );
}
