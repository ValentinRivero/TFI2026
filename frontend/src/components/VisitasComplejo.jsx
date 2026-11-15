import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { formatearEntero, formatearFechaCorta } from '../utils/formatos.js';
import { anchoDeBarra, maximoDe } from '../utils/reportes.js';
import Cargando from './Cargando.jsx';
import TarjetaReporte from './TarjetaReporte.jsx';

/**
 * Visitas al perfil del complejo y consultas de su grilla por día, de `backend-node`. Es una métrica secundaria: si el
 * servicio no responde, solo esta tarjeta muestra un aviso con "Reintentar" y el resto del dashboard sigue visible.
 * `consulta` es lo que devuelve `useConsulta` (`datos`, `error`, `cargando`, `recargar`).
 */
export default function VisitasComplejo({ consulta }) {
  const { datos, error, cargando } = consulta;
  const porDia = datos?.por_dia ?? [];
  const mayor = maximoDe(porDia, 'visitas');

  return (
    <TarjetaReporte titulo={t('reportes.visitas')} descripcion={t('reportes.visitasDescripcion')}>
      {cargando && <Cargando variante="seccion" />}
      {!cargando && error && (
        <div>
          <p className="text-secondary">{t('reportes.visitasNoDisponible')}</p>
          <Button variant="outline-secondary" size="sm" onClick={consulta.recargar}>{t('comun.reintentar')}</Button>
        </div>
      )}
      {!cargando && !error && datos && (
        <>
          <p className="mb-3 num">
            {t('reportes.visitasTotales', {
              visitas: formatearEntero(datos.totales.visitas),
              consultas: formatearEntero(datos.totales.consultas_grilla),
            })}
          </p>
          <div className="serie-columnas" role="img" aria-label={t('reportes.visitasSerie', { visitas: formatearEntero(datos.totales.visitas) })}>
            {porDia.map((dia) => (
              <div
                key={dia.fecha}
                className="serie-columna"
                title={t('reportes.visitasDia', { fecha: formatearFechaCorta(dia.fecha), visitas: dia.visitas })}
              >
                <div className="serie-columna-relleno" style={{ height: `${anchoDeBarra(dia.visitas, mayor)}%` }} />
              </div>
            ))}
          </div>
          {porDia.length > 0 && (
            <div className="d-flex justify-content-between small text-secondary num mt-1">
              <span>{formatearFechaCorta(porDia[0].fecha)}</span>
              <span>{formatearFechaCorta(porDia[porDia.length - 1].fecha)}</span>
            </div>
          )}
        </>
      )}
    </TarjetaReporte>
  );
}
