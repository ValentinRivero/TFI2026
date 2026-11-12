import { t } from '../i18n/index.js';
import { pronosticoDeFecha } from '../utils/clima.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import Cargando from './Cargando.jsx';
import ClimaCard from './ClimaCard.jsx';
import GrillaDia from './GrillaDia.jsx';
import ResumenTurno from './ResumenTurno.jsx';
import SelectorFechaGrilla from './SelectorFechaGrilla.jsx';

/**
 * Turnos del día: selector de fecha con su pronóstico, grilla en vivo y resumen del turno elegido. Solo dibuja: la
 * consulta (`grilla`), la grilla de la fecha visible (`grillaDelDia`, o `null` mientras llega), el canal en vivo
 * (`enVivo`), la elección (`turno`, de `useSeleccionTurno`) y el clima (`clima`, de `useClima`) los entrega la página.
 */
export default function SeccionTurnos({ fecha, hoy, onCambiarFecha, grilla, grillaDelDia, enVivo, turno, clima }) {
  const noDisponible = grilla.error?.status === 404;
  const climaDelDia = pronosticoDeFecha(clima.datos, fecha);

  return (
    <section aria-labelledby="detalle-turnos">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <h2 id="detalle-turnos" className="h4 mb-0">{t('grilla.titulo')}</h2>
        {enVivo.estado === 'conectado' && <span className="badge badge-ok">{t('grilla.enVivo')}</span>}
        {enVivo.estado === 'reconectando' && <span className="badge badge-aviso">{t('grilla.reconectando')}</span>}
      </div>

      <SelectorFechaGrilla fecha={fecha} hoy={hoy} onCambiar={onCambiarFecha}>
        <ClimaCard {...clima} variante="dia" fecha={fecha} />
      </SelectorFechaGrilla>

      {noDisponible && (
        <Alerta variante="warning" titulo={t('grilla.noDisponibleTitulo')}>{t('grilla.noDisponibleDescripcion')}</Alerta>
      )}

      {grilla.error && !noDisponible && (
        <AlertaReintento titulo={t('grilla.errorTitulo')} mensaje={grilla.error.mensaje} onReintentar={grilla.recargar} />
      )}

      {!grilla.error && !grillaDelDia && <Cargando variante="seccion" />}

      {!grilla.error && grillaDelDia && (
        <div className="d-grid gap-3" aria-busy={grilla.cargando}>
          {turno.perdida && <Alerta variante="warning" className="mb-0">{t('grilla.seleccionPerdida')}</Alerta>}
          <GrillaDia grilla={grillaDelDia} seleccion={turno.seleccion} onElegir={turno.elegir} />
          {turno.vigente ? (
            <ResumenTurno cancha={turno.cancha} bloque={turno.bloque} fecha={fecha} onQuitar={turno.quitar}>
              {climaDelDia && <ClimaCard {...clima} variante="dia" fecha={fecha} />}
            </ResumenTurno>
          ) : (
            grillaDelDia.canchas.length > 0 && <p className="text-secondary small mb-0">{t('grilla.ayuda')}</p>
          )}
        </div>
      )}
    </section>
  );
}
