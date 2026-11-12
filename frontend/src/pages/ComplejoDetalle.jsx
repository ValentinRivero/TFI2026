import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import AlertaReintento from '../components/AlertaReintento.jsx';
import BotonVolver from '../components/BotonVolver.jsx';
import Cargando from '../components/Cargando.jsx';
import ClimaCard from '../components/ClimaCard.jsx';
import EncabezadoComplejo from '../components/EncabezadoComplejo.jsx';
import EstadoVacio from '../components/EstadoVacio.jsx';
import FichaComplejo from '../components/FichaComplejo.jsx';
import SeccionCanchas from '../components/SeccionCanchas.jsx';
import SeccionTurnos from '../components/SeccionTurnos.jsx';
import useClima from '../hooks/useClima.js';
import useConsulta from '../hooks/useConsulta.js';
import useDisponibilidadEnVivo from '../hooks/useDisponibilidadEnVivo.js';
import useRegistroActividad from '../hooks/useRegistroActividad.js';
import useSeleccionTurno from '../hooks/useSeleccionTurno.js';
import { t } from '../i18n/index.js';
import { obtenerComplejo, obtenerGrilla } from '../services/complejoService.js';
import { aFechaIso } from '../utils/formatos.js';

const ES_ID = /^[1-9]\d{0,9}$/;

function ComplejoNoEncontrado() {
  return (
    <EstadoVacio titulo={t('complejo.noEncontradoTitulo')} descripcion={t('complejo.noEncontradoDescripcion')}>
      <BotonVolver destino="/">{t('complejo.volver')}</BotonVolver>
    </EstadoVacio>
  );
}

function DetalleDeComplejo({ id }) {
  const [hoy] = useState(() => aFechaIso(new Date()));
  const [fecha, setFecha] = useState(hoy);

  const complejo = useConsulta((signal) => obtenerComplejo(id, signal), [id]);
  const clima = useClima(id);
  // `useConsulta` cancela la petición en vuelo al cambiar de fecha: una respuesta lenta no pisa a la más nueva.
  const grilla = useConsulta((signal) => obtenerGrilla(id, fecha, signal), [id, fecha]);

  // Mientras llega la grilla de una fecha nueva, la anterior queda en `datos` pero no se muestra.
  const grillaDelDia = grilla.datos?.fecha === fecha ? grilla.datos : null;
  const canchas = grillaDelDia?.canchas ?? null;
  const canchaIds = useMemo(() => canchas?.map((cancha) => cancha.id) ?? null, [canchas]);

  const turno = useSeleccionTurno(fecha, canchas);
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
      <SeccionCanchas canchas={complejo.datos.canchas} />
      <SeccionTurnos
        fecha={fecha}
        hoy={hoy}
        onCambiarFecha={setFecha}
        grilla={grilla}
        grillaDelDia={grillaDelDia}
        enVivo={enVivo}
        turno={turno}
        clima={clima}
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
