import Button from 'react-bootstrap/Button';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';
import ComplejoCard from './ComplejoCard.jsx';
import EstadoVacio from './EstadoVacio.jsx';

/**
 * Resultados del catálogo con todos sus estados: carga, error con reintento, vacío (con o sin filtros) y tarjetas
 * con "Mostrar más". `lista` es lo que devuelve `useListaIncremental`.
 */
export default function ListaComplejos({ lista, hayFiltros, onLimpiar }) {
  const { items, total, hayMas, cargando, cargandoMas, error, errorMas, cargarMas, recargar } = lista;
  const limpiar = hayFiltros && <Button variant="outline-secondary" onClick={onLimpiar}>{t('filtros.limpiar')}</Button>;

  return (
    <section aria-labelledby="catalogo-listado" aria-busy={cargando}>
      <h2 id="catalogo-listado" className="visually-hidden">{t('catalogo.listado')}</h2>

      {cargando && <Cargando variante="seccion" />}

      {!cargando && error && (
        <AlertaReintento titulo={t('catalogo.errorTitulo')} mensaje={error.mensaje} onReintentar={recargar}>
          {limpiar}
        </AlertaReintento>
      )}

      {!cargando && !error && items.length === 0 && (
        <EstadoVacio
          titulo={t('catalogo.vacioTitulo')}
          descripcion={hayFiltros ? t('catalogo.vacioFiltros') : t('catalogo.vacioSinFiltros')}
        >
          {hayFiltros && <Button variant="outline-primary" onClick={onLimpiar}>{t('filtros.limpiar')}</Button>}
        </EstadoVacio>
      )}

      {!cargando && !error && items.length > 0 && (
        <>
          <p className="text-secondary small" role="status">
            {t('comun.resumenComplejos', { mostrados: items.length, total })}
          </p>
          <div className="row g-3 row-cols-1 row-cols-md-2 row-cols-lg-3">
            {items.map((complejo) => (
              <div key={complejo.id} className="col">
                <ComplejoCard complejo={complejo} />
              </div>
            ))}
          </div>
          {errorMas && <Alerta variante="warning" className="mt-3">{t('catalogo.errorMas')} {errorMas.mensaje}</Alerta>}
          {hayMas && (
            <div className="text-center mt-4">
              <BotonAccion variant="outline-primary" cargando={cargandoMas} onClick={cargarMas}>
                {t('comun.mostrarMas')}
              </BotonAccion>
            </div>
          )}
        </>
      )}
    </section>
  );
}
