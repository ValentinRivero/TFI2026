import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { puedeVer } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import { crearReserva } from '../services/reservaService.js';
import { formatearHora } from '../utils/formatos.js';
import { aParametrosRetorno } from '../utils/retornoReserva.js';
import useSesion from './useSesion.js';

export const RESULTADO_RESERVA = Object.freeze({ CREADA: 'creada', OCUPADO: 'ocupado' });

/**
 * Flujo de reserva del turno elegido (`turno`, de `useSeleccionTurno`) en la fecha `fecha`.
 * - Sin sesión, `abrir` lleva al login conservando complejo, fecha y casillero; al volver, `retomar`
 *   (`{ fecha, canchaId, horaInicio }`) reabre la confirmación de ese mismo turno si sigue libre.
 * - Con sesión, `abrir` muestra la confirmación y `confirmar` crea la reserva. Un 409 (el turno acaba de ocuparse)
 *   limpia la selección y pide recargar la grilla; el resto de los errores quedan en `error`, dentro de la confirmación.
 * - `resultado` es el aviso de lo último que pasó (`CREADA` u `OCUPADO`) hasta que se descarte.
 * `alCambiarGrilla` recarga la grilla cuando el turno cambió de estado.
 */
export default function useReservaTurno({ complejoId, fecha, turno, alCambiarGrilla, retomar = null }) {
  const { autenticado, rol } = useSesion();
  const navegar = useNavigate();
  const [estado, setEstado] = useState({ abierto: false, retomar, error: null });
  const [resultado, setResultado] = useState(null);

  const permitida = !autenticado || puedeVer('reservar', rol);
  // Retomar vale solo para el turno que se había elegido antes del login, no para otro que se elija después.
  const { seleccion } = turno;
  const esElTurnoARetomar = Boolean(estado.retomar && seleccion)
    && estado.retomar.fecha === fecha
    && estado.retomar.canchaId === seleccion.canchaId
    && formatearHora(estado.retomar.horaInicio) === formatearHora(seleccion.horaInicio);
  // La confirmación se muestra solo mientras el turno siga libre: si lo ocupan en vivo, se cierra sola.
  const abierto = autenticado && permitida && turno.vigente && (estado.abierto || esElTurnoARetomar);

  const cerrar = () => setEstado({ abierto: false, retomar: null, error: null });

  const abrir = () => {
    if (!turno.vigente || !permitida) return;
    if (!autenticado) {
      const retorno = aParametrosRetorno({ fecha, canchaId: turno.cancha.id, horaInicio: turno.bloque.hora_inicio });
      navegar('/login', {
        state: {
          desde: { pathname: `/complejos/${complejoId}`, search: `?${retorno}` },
          aviso: t('reserva.iniciarSesion'),
        },
      });
      return;
    }
    setResultado(null);
    setEstado({ abierto: true, retomar: null, error: null });
  };

  const confirmar = async () => {
    if (!turno.vigente) return;
    setEstado((actual) => ({ ...actual, error: null }));
    try {
      await crearReserva({ canchaId: turno.cancha.id, fechaTurno: fecha, horaInicio: turno.bloque.hora_inicio });
    } catch (falla) {
      if (falla.status === 409) {
        cerrar();
        turno.quitar();
        setResultado({ tipo: RESULTADO_RESERVA.OCUPADO, mensaje: falla.mensaje });
        alCambiarGrilla();
      } else {
        setEstado((actual) => ({ ...actual, error: falla }));
      }
      return;
    }
    cerrar();
    turno.quitar();
    setResultado({ tipo: RESULTADO_RESERVA.CREADA });
    alCambiarGrilla();
  };

  return {
    abierto,
    permitida,
    error: estado.error,
    resultado,
    abrir,
    cerrar,
    confirmar,
    descartarResultado: () => setResultado(null),
  };
}
