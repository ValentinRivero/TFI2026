import { t } from '../i18n/index.js';
import { pronosticoDeFecha } from '../utils/clima.js';
import { nacerSinCancelacion } from '../utils/reservas.js';
import Alerta from './Alerta.jsx';
import AlertaReintento from './AlertaReintento.jsx';
import Cargando from './Cargando.jsx';
import ClimaCard from './ClimaCard.jsx';
import AvisoReserva from './AvisoReserva.jsx';
import GrillaDia from './GrillaDia.jsx';
import ModalReservar from './ModalReservar.jsx';
import ResumenCancha from './ResumenCancha.jsx';
import ResumenTurno from './ResumenTurno.jsx';
import SelectorFechaGrilla from './SelectorFechaGrilla.jsx';

/**
 * Turnos del día de la cancha elegida (`cancha`, la ficha pública, o `null` si todavía no se eligió): selector de fecha
 * con su pronóstico, resumen de la cancha, su grilla en vivo, resumen del turno elegido y confirmación de la reserva.
 * Solo dibuja: la consulta (`grilla`), la grilla de la fecha visible (`grillaDelDia`, o `null` mientras
 * llega), el canal en vivo (`enVivo`), la elección (`turno`, de `useSeleccionTurno`), el clima (`clima`, de
 * `useClima`), el flujo de reserva (`reserva`, de `useReservaTurno`) y el `complejo` los entrega la página.
 */
export default function SeccionTurnos({
  complejo,
  cancha,
  fecha,
  hoy,
  onCambiarFecha,
  grilla,
  grillaDelDia,
  enVivo,
  turno,
  clima,
  reserva,
}) {
  const noDisponible = grilla.error?.status === 404;
  // Solo se dibuja la grilla de la cancha elegida, aunque la consulta traiga todas las del complejo.
  const grillaDeCancha = grillaDelDia && cancha
    ? { ...grillaDelDia, canchas: grillaDelDia.canchas.filter((candidata) => candidata.id === cancha.id) }
    : null;
  const climaDelDia = pronosticoDeFecha(clima.datos, fecha);
  const horasCancelacion = complejo.horas_limite_cancelacion;
  // Se evalúa al dibujar con el turno elegido: si ya está dentro del margen, se advierte antes de reservar.
  const horasSinCancelacion = turno.bloque
    && nacerSinCancelacion(fecha, turno.bloque.hora_inicio, horasCancelacion) ? horasCancelacion : null;

  return (
    <section aria-labelledby="detalle-turnos">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <h2 id="detalle-turnos" className="h4 mb-0">{t('grilla.titulo')}</h2>
        {enVivo.estado === 'conectado' && <span className="badge badge-ok">{t('grilla.enVivo')}</span>}
        {enVivo.estado === 'reconectando' && <span className="badge badge-aviso">{t('grilla.reconectando')}</span>}
      </div>

      {!cancha ? (
        <p className="text-secondary mb-0">{t('grilla.elegirCanchaPrimero')}</p>
      ) : (
        <>
          <SelectorFechaGrilla fecha={fecha} hoy={hoy} onCambiar={onCambiarFecha}>
            <ClimaCard {...clima} variante="dia" fecha={fecha} />
          </SelectorFechaGrilla>

          <div className="mb-3"><ResumenCancha cancha={cancha} /></div>

          {noDisponible && (
            <Alerta variante="warning" titulo={t('grilla.noDisponibleTitulo')}>{t('grilla.noDisponibleDescripcion')}</Alerta>
          )}

          {grilla.error && !noDisponible && (
            <AlertaReintento titulo={t('grilla.errorTitulo')} mensaje={grilla.error.mensaje} onReintentar={grilla.recargar} />
          )}

          {!grilla.error && !grillaDelDia && <Cargando variante="seccion" />}

          {!grilla.error && grillaDelDia && (
            <div className="d-grid gap-3" aria-busy={grilla.cargando}>
              {reserva.resultado && <AvisoReserva resultado={reserva.resultado} onCerrar={reserva.descartarResultado} />}
              {turno.perdida && <Alerta variante="warning" className="mb-0">{t('grilla.seleccionPerdida')}</Alerta>}
              <GrillaDia grilla={grillaDeCancha} seleccion={turno.seleccion} onElegir={turno.elegir} />
              {turno.vigente ? (
                <>
                  <ResumenTurno
                    cancha={turno.cancha}
                    bloque={turno.bloque}
                    fecha={fecha}
                    onReservar={reserva.permitida ? reserva.abrir : undefined}
                    onQuitar={turno.quitar}
                    horasSinCancelacion={horasSinCancelacion}
                    nota={reserva.permitida ? null : t('reserva.rolSinReserva')}
                  >
                    {climaDelDia && <ClimaCard {...clima} variante="dia" fecha={fecha} />}
                  </ResumenTurno>
                  <ModalReservar
                    mostrar={reserva.abierto}
                    complejo={complejo}
                    cancha={turno.cancha}
                    bloque={turno.bloque}
                    fecha={fecha}
                    clima={clima}
                    error={reserva.error}
                    horasSinCancelacion={horasSinCancelacion}
                    onConfirmar={reserva.confirmar}
                    onCancelar={reserva.cerrar}
                  />
                </>
              ) : (
                grillaDeCancha.canchas.length > 0 && <p className="text-secondary small mb-0">{t('grilla.ayuda')}</p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
