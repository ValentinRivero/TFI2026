import { useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import AlertaReintento from '../components/AlertaReintento.jsx';
import Cargando from '../components/Cargando.jsx';
import ClimaCard from '../components/ClimaCard.jsx';
import ComplejoNoEncontrado from '../components/ComplejoNoEncontrado.jsx';
import EncabezadoComplejo from '../components/EncabezadoComplejo.jsx';
import FichaComplejo from '../components/FichaComplejo.jsx';
import SeccionCanchas from '../components/SeccionCanchas.jsx';
import SeccionTurnos from '../components/SeccionTurnos.jsx';
import useCanchaElegida from '../hooks/useCanchaElegida.js';
import useClima from '../hooks/useClima.js';
import useConsulta from '../hooks/useConsulta.js';
import useDisponibilidadEnVivo from '../hooks/useDisponibilidadEnVivo.js';
import useRegistroActividad from '../hooks/useRegistroActividad.js';
import useReservaTurno from '../hooks/useReservaTurno.js';
import useSeleccionTurno from '../hooks/useSeleccionTurno.js';
import { t } from '../i18n/index.js';
import { obtenerComplejo, obtenerGrilla } from '../services/complejoService.js';
import { aFechaIso } from '../utils/formatos.js';
import { leerRetorno } from '../utils/retornoReserva.js';

const ES_ID = /^[1-9]\d{0,9}$/;

function DetalleDeComplejo({ id }) {
  const [parametros, setParametros] = useSearchParams();
  // El turno a retomar (al volver del login) se lee una sola vez y se limpia de la URL.
  const [retorno] = useState(() => leerRetorno(parametros));
  const [hoy] = useState(() => aFechaIso(new Date()));
  const [fecha, setFecha] = useState(retorno?.fecha ?? hoy);

  useEffect(() => {
    if (retorno && parametros.size > 0) setParametros(new URLSearchParams(), { replace: true });
  }, [retorno, parametros, setParametros]);

  const complejo = useConsulta((signal) => obtenerComplejo(id, signal), [id]);
  const clima = useClima(id);
  // `useConsulta` cancela la petición en vuelo al cambiar de fecha: una respuesta lenta no pisa a la más nueva.
  const grilla = useConsulta((signal) => obtenerGrilla(id, fecha, signal), [id, fecha]);

  // Mientras llega la grilla de una fecha nueva, la anterior queda en `datos` pero no se muestra.
  const grillaDelDia = grilla.datos?.fecha === fecha ? grilla.datos : null;
  const canchas = grillaDelDia?.canchas ?? null;
  const canchaIds = useMemo(() => canchas?.map((cancha) => cancha.id) ?? null, [canchas]);

  const fichasDeCanchas = complejo.datos?.canchas ?? null;
  const cancha = useCanchaElegida(fichasDeCanchas, retorno?.canchaId ?? null);
  // El turno se valida solo contra la cancha elegida: el resto de las grillas no se muestra.
  const canchasDeLaElegida = useMemo(
    () => canchas?.filter((candidata) => candidata.id === cancha.cancha?.id) ?? null,
    [canchas, cancha.cancha?.id],
  );
  const turno = useSeleccionTurno(fecha, canchasDeLaElegida, retorno);
  const reserva = useReservaTurno({
    complejoId: id,
    fecha,
    turno,
    alCambiarGrilla: grilla.recargar,
    retomar: retorno?.reservar ? retorno : null,
  });
  const enVivo = useDisponibilidadEnVivo({
    complejoId: id,
    habilitado: Boolean(complejo.datos) && grilla.error?.status !== 404,
    fecha,
    canchaIds,
    alRecargar: grilla.recargar,
  });
  useRegistroActividad({
    complejoId: id,
    complejoCargado: Boolean(complejo.datos),
    fechaGrilla: grilla.datos?.fecha ?? null,
  });

  // Al cambiar de cancha se descarta el casillero que había elegido en otra.
  const elegirCancha = (id) => {
    if (id === cancha.cancha?.id) return;
    turno.quitar();
    cancha.elegir(id);
  };

  if (complejo.error?.status === 404) return <ComplejoNoEncontrado />;
  if (complejo.error) {
    return <AlertaReintento titulo={t('complejo.errorTitulo')} mensaje={complejo.error.mensaje} onReintentar={complejo.recargar} />;
  }
  if (!complejo.datos) return <Cargando variante="seccion" />;

  return (
    <div>
      <EncabezadoComplejo complejo={complejo.datos} />
      <div className="row g-3 mb-4">
        <div className="col-lg-6"><FichaComplejo complejo={complejo.datos} /></div>
        <div className="col-lg-6"><ClimaCard {...clima} variante="detalle" /></div>
      </div>
      <SeccionCanchas
        canchas={complejo.datos.canchas}
        seleccionadaId={cancha.cancha?.id ?? null}
        onElegir={elegirCancha}
      />
      <SeccionTurnos
        complejo={complejo.datos}
        cancha={cancha.cancha}
        fecha={fecha}
        hoy={hoy}
        onCambiarFecha={setFecha}
        grilla={grilla}
        grillaDelDia={grillaDelDia}
        enVivo={enVivo}
        turno={turno}
        clima={clima}
        reserva={reserva}
      />
    </div>
  );
}

/** Ficha pública de un complejo: datos comerciales, clima, canchas y la grilla del día en vivo. */
export default function ComplejoDetalle() {
  const { id } = useParams();
  // `key` reinicia el estado de la pantalla al pasar de un complejo a otro.
  return ES_ID.test(id ?? '') ? <DetalleDeComplejo key={id} id={id} /> : <ComplejoNoEncontrado />;
}
