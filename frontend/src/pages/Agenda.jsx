import { useSearchParams } from 'react-router-dom';
import EncabezadoPantalla from '../components/EncabezadoPantalla.jsx';
import PestanasAgenda from '../components/PestanasAgenda.jsx';
import SeccionReservasAgenda from '../components/SeccionReservasAgenda.jsx';
import SeccionTurnosFijos from '../components/SeccionTurnosFijos.jsx';
import { PESTANAS_AGENDA, VISTA_AGENDA } from '../config/catalogos.js';
import useAgenda from '../hooks/useAgenda.js';
import useCanchasDelComplejo from '../hooks/useCanchasDelComplejo.js';
import useContextoPanel from '../hooks/useContextoPanel.js';
import useTurnosFijos from '../hooks/useTurnosFijos.js';
import { t } from '../i18n/index.js';
import { vistaDeAgenda } from '../utils/agenda.js';

/**
 * Agenda operativa del complejo activo: las reservas del día (con alta manual, cambios de estado, cancelación y
 * reapertura) y los turnos fijos. La vista activa viaja en `?vista=` para poder compartir el enlace; cambiarla no
 * apila entradas en el historial. Solo la vista visible consulta al backend.
 */
export default function Agenda() {
  const { complejo } = useContextoPanel();
  const [params, setParams] = useSearchParams();
  const vista = vistaDeAgenda(params.get('vista'));
  const canchas = useCanchasDelComplejo(complejo.id);
  const agenda = useAgenda(complejo.id, { habilitado: vista === VISTA_AGENDA.RESERVAS });
  const turnos = useTurnosFijos(complejo.id, { habilitado: vista === VISTA_AGENDA.TURNOS_FIJOS, canchas });

  const cambiarVista = (nueva) => setParams(nueva === VISTA_AGENDA.RESERVAS ? {} : { vista: nueva }, { replace: true });

  return (
    <div>
      <EncabezadoPantalla titulo={t('agenda.titulo')} descripcion={t('agenda.descripcion')} />
      <PestanasAgenda pestanas={PESTANAS_AGENDA} activa={vista} onCambiar={cambiarVista} />
      {vista === VISTA_AGENDA.RESERVAS
        ? <SeccionReservasAgenda agenda={agenda} canchas={canchas} />
        : <SeccionTurnosFijos turnos={turnos} canchas={canchas} />}
    </div>
  );
}
