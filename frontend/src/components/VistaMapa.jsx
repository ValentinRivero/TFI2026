import { lazy, Suspense, useMemo } from 'react';
import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import { armarMarcadores } from '../utils/mapa.js';
import AlertaReintento from './AlertaReintento.jsx';
import Cargando from './Cargando.jsx';
import EstadoVacio from './EstadoVacio.jsx';

// Leaflet y su CSS viajan en este bloque: la vista de lista nunca los descarga.
const MapaComplejos = lazy(() => import('./MapaComplejos.jsx'));

/**
 * Vista de mapa del catálogo con todos sus estados: carga, error con reintento, vacío (sin complejos con ubicación)
 * y mapa. `consulta` es lo que devuelve `useConsulta` sobre los marcadores; mientras llegan los de un filtro nuevo
 * el mapa sigue en pantalla con los anteriores, para no volver a montarlo en cada cambio.
 */
export default function VistaMapa({ consulta, hayFiltros, onLimpiar, onAbrirComplejo }) {
  const { datos, error, cargando, recargar } = consulta;
  const marcadores = useMemo(() => armarMarcadores(datos), [datos]);
  const primeraCarga = cargando && marcadores.length === 0;

  return (
    <section aria-labelledby="catalogo-mapa" aria-busy={cargando}>
      <h2 id="catalogo-mapa" className="visually-hidden">{t('mapa.titulo')}</h2>

      {primeraCarga && <Cargando variante="seccion" />}

      {!cargando && error && (
        <AlertaReintento titulo={t('mapa.errorTitulo')} mensaje={error.mensaje} onReintentar={recargar}>
          {hayFiltros && <Button variant="outline-secondary" onClick={onLimpiar}>{t('filtros.limpiar')}</Button>}
        </AlertaReintento>
      )}

      {!cargando && !error && marcadores.length === 0 && (
        <EstadoVacio
          titulo={t('mapa.vacioTitulo')}
          descripcion={hayFiltros ? t('mapa.vacioFiltros') : t('mapa.vacioSinFiltros')}
        >
          {hayFiltros && <Button variant="outline-primary" onClick={onLimpiar}>{t('filtros.limpiar')}</Button>}
        </EstadoVacio>
      )}

      {!error && marcadores.length > 0 && (
        <>
          <p className="text-secondary small" role="status">{t('mapa.resumen', { cantidad: marcadores.length })}</p>
          <Suspense fallback={<Cargando variante="seccion" texto={t('mapa.cargando')} />}>
            <MapaComplejos marcadores={marcadores} alAbrir={onAbrirComplejo} />
          </Suspense>
        </>
      )}
    </section>
  );
}
