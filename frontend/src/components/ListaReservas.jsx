import Button from 'react-bootstrap/Button';
import { Link } from 'react-router-dom';
import { VIGENCIA_RESERVA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import BotonAccion from './BotonAccion.jsx';
import Cargando from './Cargando.jsx';
import EstadoVacio from './EstadoVacio.jsx';
import ReservaRow from './ReservaRow.jsx';

/**
 * Reservas de la vista elegida con todos sus estados: carga, error con reintento, vacío y filas con "Mostrar más".
 * `lista` es lo que devuelve `useListaIncremental`; `onCancelar` recibe la reserva que se quiere cancelar.
 */
export default function ListaReservas({ lista, vigencia, onCancelar }) {
  const { items, total, hayMas, cargando, cargandoMas, error, errorMas, cargarMas, recargar } = lista;
  const proximas = vigencia === VIGENCIA_RESERVA.PROXIMAS;

  return (
    <section aria-label={t(proximas ? 'misReservas.proximas' : 'misReservas.historial')} aria-busy={cargando}>
      {cargando && <Cargando variante="seccion" />}

      {!cargando && error && (
        <AlertaReintento titulo={t('misReservas.errorTitulo')} mensaje={error.mensaje} onReintentar={recargar} />
      )}

      {!cargando && !error && items.length === 0 && (
        <EstadoVacio
          titulo={t(proximas ? 'misReservas.vacioProximasTitulo' : 'misReservas.vacioHistorialTitulo')}
          descripcion={t(proximas ? 'misReservas.vacioProximasDescripcion' : 'misReservas.vacioHistorialDescripcion')}
        >
          {proximas && <Button as={Link} to="/" variant="outline-primary">{t('misReservas.explorar')}</Button>}
        </EstadoVacio>
      )}

      {!cargando && !error && items.length > 0 && (
        <>
          <p className="text-secondary small" role="status">
            {t('misReservas.resumen', { mostradas: items.length, total })}
          </p>
          <div className="d-grid gap-3">
            {items.map((reserva) => <ReservaRow key={reserva.id} reserva={reserva} onCancelar={onCancelar} />)}
          </div>
          {errorMas && <Alerta variante="warning" className="mt-3">{t('misReservas.errorMas')} {errorMas.mensaje}</Alerta>}
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
