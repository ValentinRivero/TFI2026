import { useState } from 'react';
import { ESTADOS_REAPERTURA } from '../config/catalogos.js';
import { t } from '../i18n/index.js';
import {
  actualizarReservaAgenda,
  cancelarReservaAgenda,
  crearReservaManual,
  listarAgenda,
  reabrirReserva,
} from '../services/reservaService.js';
import {
  cuerpoReservaManual,
  filtrosAgendaIniciales,
  validarReservaManual,
  VALORES_RESERVA_MANUAL_INICIALES,
} from '../utils/agenda.js';
import { leerConflictos } from '../utils/conflictos.js';
import { aFechaIso } from '../utils/formatos.js';
import useBloquesDeCancha from './useBloquesDeCancha.js';
import useConfirmacion from './useConfirmacion.js';
import useEnvio from './useEnvio.js';
import useFiltros from './useFiltros.js';
import useListaPaginada from './useListaPaginada.js';

const ESTADO_REAPERTURA_INICIAL = String(ESTADOS_REAPERTURA[0]);

/**
 * Agenda operativa del complejo activo: lista paginada de reservas con filtros (día, cancha, estado y conflictos de
 * operatoria), alta manual (telefónica o presencial), cambio de estado, cancelación por el complejo y reapertura de
 * una cancelada. El horario del alta se elige en la mini-grilla real de la cancha y el día (`bloques`), mantenida al
 * día en vivo. La reapertura valida el turno en el servidor y pide una confirmación explícita (`409` con
 * `requiere_confirmacion`) antes de volver a ocupar el casillero.
 */
export default function useAgenda(complejoId, { habilitado = true } = {}) {
  const hoy = aFechaIso(new Date());
  const { filtros, cambiar: cambiarFiltro, limpiar: limpiarFiltros } = useFiltros(filtrosAgendaIniciales(hoy));
  const lista = useListaPaginada(
    async (pagina, signal) => (habilitado
      ? listarAgenda(complejoId, filtros, pagina, signal)
      : { count: 0, results: [] }),
    [complejoId, filtros, habilitado],
  );

  const [aviso, setAviso] = useState(null);
  const [errorAccion, setErrorAccion] = useState(null);
  const [cambiando, setCambiando] = useState(null);

  const informar = (clave) => {
    setErrorAccion(null);
    setAviso(t(clave));
  };

  const [altaAbierta, setAltaAbierta] = useState(false);
  const [valores, setValores] = useState(VALORES_RESERVA_MANUAL_INICIALES);
  const [intentado, setIntentado] = useState(false);
  const alta = useEnvio();
  const erroresLocales = validarReservaManual(valores, hoy);
  const errores = { ...(intentado ? erroresLocales : {}), ...(alta.error?.campos ?? {}) };

  const abrirAlta = () => {
    alta.limpiar();
    setIntentado(false);
    setValores({ ...VALORES_RESERVA_MANUAL_INICIALES, fecha_turno: filtros.fecha || hoy });
    setAltaAbierta(true);
  };

  const cerrarAlta = () => {
    alta.limpiar();
    setAltaAbierta(false);
  };

  const bloques = useBloquesDeCancha({
    complejoId,
    canchaId: valores.cancha,
    fecha: valores.fecha_turno,
    hoy,
    habilitado: altaAbierta,
  });

  // Otra cancha u otro día cambian la grilla: el horario elegido deja de valer.
  const cambiarValor = (campo, valor) => {
    alta.limpiar();
    setValores((actuales) => ({
      ...actuales,
      [campo]: valor,
      ...(campo === 'cancha' || campo === 'fecha_turno' ? { hora_inicio: '' } : {}),
    }));
  };

  const registrar = async (evento) => {
    evento.preventDefault();
    setIntentado(true);
    if (Object.keys(erroresLocales).length > 0) return;
    const resultado = await alta.enviar(() => crearReservaManual(cuerpoReservaManual(valores)));
    if (!resultado.ok) return;
    setAltaAbierta(false);
    setAviso(t('agenda.avisoAlta'));
    setErrorAccion(null);
    lista.recargar();
  };

  const cambiarEstado = async (reserva, estado) => {
    setAviso(null);
    setErrorAccion(null);
    setCambiando(reserva.id);
    try {
      await actualizarReservaAgenda(reserva.id, { estado });
      informar('agenda.avisoEstado');
    } catch (error) {
      setErrorAccion(error);
    } finally {
      setCambiando(null);
      lista.recargar();
    }
  };

  const cancelacion = useConfirmacion((reserva) => cancelarReservaAgenda(reserva.id), {
    alExito: () => {
      informar('agenda.avisoCancelada');
      lista.recargar();
    },
    alError: (error) => {
      if (error.status === 404) lista.recargar();
    },
  });

  const [reapertura, setReapertura] = useState({ reserva: null, estado: ESTADO_REAPERTURA_INICIAL, conflicto: null });
  const reabrir = useEnvio();

  const pedirReapertura = (reserva) => {
    reabrir.limpiar();
    setAviso(null);
    setReapertura({ reserva, estado: ESTADO_REAPERTURA_INICIAL, conflicto: null });
  };

  const cerrarReapertura = () => {
    reabrir.limpiar();
    setReapertura({ reserva: null, estado: ESTADO_REAPERTURA_INICIAL, conflicto: null });
  };

  const terminarReapertura = () => {
    cerrarReapertura();
    informar('agenda.avisoReabierta');
    lista.recargar();
  };

  // Primer paso: el servidor revalida el turno y, si está libre, responde 409 con la vista previa a confirmar.
  const continuarReapertura = async () => {
    const { reserva, estado } = reapertura;
    const resultado = await reabrir.enviar(() => reabrirReserva(reserva.id, Number(estado), false));
    if (resultado.ok) {
      terminarReapertura();
      return;
    }
    const conflicto = leerConflictos(resultado.error);
    if (conflicto) {
      reabrir.limpiar();
      setReapertura((actual) => ({ ...actual, conflicto }));
    } else if (resultado.error.status === 404) {
      lista.recargar();
    }
  };

  const confirmarReapertura = async () => {
    const { reserva, estado } = reapertura;
    const resultado = await reabrir.enviar(() => reabrirReserva(reserva.id, Number(estado), true));
    if (resultado.ok) terminarReapertura();
  };

  return {
    lista,
    filtros,
    cambiarFiltro,
    limpiarFiltros,
    aviso,
    descartarAviso: () => setAviso(null),
    errorAccion,
    descartarError: () => setErrorAccion(null),
    cambiando,
    cambiarEstado,
    alta: {
      abierta: altaAbierta,
      valores,
      errores,
      error: alta.error,
      enviando: alta.enviando,
      hoy,
      bloques,
      abrir: abrirAlta,
      cerrar: cerrarAlta,
      cambiar: cambiarValor,
      enviar: registrar,
    },
    cancelacion,
    reapertura: {
      ...reapertura,
      error: reabrir.error,
      enviando: reabrir.enviando,
      pedir: pedirReapertura,
      cambiarEstado: (estado) => setReapertura((actual) => ({ ...actual, estado })),
      continuar: continuarReapertura,
      confirmar: confirmarReapertura,
      cerrar: cerrarReapertura,
      volver: () => {
        reabrir.limpiar();
        setReapertura((actual) => ({ ...actual, conflicto: null }));
      },
    },
  };
}
