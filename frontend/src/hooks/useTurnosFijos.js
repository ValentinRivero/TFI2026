import { useState } from 'react';
import { ACCION_FECHA_TURNO_FIJO, TURNO_FIJO_PAUSADO, TURNO_FIJO_VIGENTE } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import {
  actualizarTurnoFijo,
  crearTurnoFijo,
  darDeBajaTurnoFijo,
  listarTurnosEnEspera,
  listarTurnosFijos,
  registrarFechaTurnoFijo,
} from '../services/turnoFijoService.js';
import { conConfirmacion, leerConflictos } from '../utils/conflictos.js';
import { aFechaIso } from '../utils/formatos.js';
import {
  aFilasEnEspera,
  cuerpoTurnoFijo,
  FILTROS_TURNOS_FIJOS_INICIALES,
  proximasFechasDeTurnoFijo,
  validarTurnoFijo,
  VALORES_TURNO_FIJO_INICIALES,
} from '../utils/turnosFijos.js';
import useBloquesDeHorario from './useBloquesDeHorario.js';
import useConfirmacion from './useConfirmacion.js';
import useEnvio from './useEnvio.js';
import useFiltros from './useFiltros.js';
import useListaPaginada from './useListaPaginada.js';

const SIN_EDICION = Object.freeze({ turno: null, hora_inicio: '', fecha_fin_vigencia: '', conflicto: null });
const SIN_FECHA = Object.freeze({ turno: null, fecha: '', accion: ACCION_FECHA_TURNO_FIJO.MANTENER });

/** Cuerpo del `PATCH` de la edición: solo lo que cambió respecto del turno fijo guardado. */
const cuerpoEdicion = (edicion) => {
  const { turno } = edicion;
  const cuerpo = {};
  if (edicion.hora_inicio && edicion.hora_inicio.slice(0, 5) !== turno.hora_inicio.slice(0, 5)) {
    cuerpo.hora_inicio = edicion.hora_inicio;
  }
  if (edicion.fecha_fin_vigencia !== (turno.fecha_fin_vigencia ?? '')) {
    cuerpo.fecha_fin_vigencia = edicion.fecha_fin_vigencia || null;
  }
  return cuerpo;
};

/**
 * Turnos fijos del complejo activo: lista paginada con filtros, alta, pausa y reanudación, edición del horario con
 * confirmación de conflictos, baja, registro de fechas puntuales en la agenda y la bandeja de fechas en espera por una
 * excepción horaria (que el complejo decide mantener o cancelar). El horario no se escribe a mano: se elige entre los
 * bloques que arma la cancha ese día de la semana (`canchas` es la lista del complejo con su duración de turno).
 */
export default function useTurnosFijos(complejoId, { habilitado = true, canchas = [] } = {}) {
  const hoy = aFechaIso(new Date());
  const { filtros, cambiar: cambiarFiltro, limpiar: limpiarFiltros } = useFiltros(FILTROS_TURNOS_FIJOS_INICIALES);
  const vacia = { count: 0, results: [] };
  const lista = useListaPaginada(
    async (pagina, signal) => (habilitado ? listarTurnosFijos(complejoId, filtros, pagina, signal) : vacia),
    [complejoId, filtros, habilitado],
  );
  const enEspera = useListaPaginada(
    async (pagina, signal) => (habilitado ? listarTurnosEnEspera(complejoId, pagina, signal) : vacia),
    [complejoId, habilitado],
  );

  const [aviso, setAviso] = useState(null);
  const [errorAccion, setErrorAccion] = useState(null);
  const [cambiando, setCambiando] = useState(null);

  const recargarTodo = () => {
    lista.recargar();
    enEspera.recargar();
  };

  const informar = (clave) => {
    setErrorAccion(null);
    setAviso(t(clave));
  };

  const [altaAbierta, setAltaAbierta] = useState(false);
  const [valores, setValores] = useState(VALORES_TURNO_FIJO_INICIALES);
  const [intentado, setIntentado] = useState(false);
  const alta = useEnvio();
  const erroresLocales = validarTurnoFijo(valores, hoy);
  const errores = { ...(intentado ? erroresLocales : {}), ...(alta.error?.campos ?? {}) };

  const abrirAlta = () => {
    alta.limpiar();
    setIntentado(false);
    setValores({ ...VALORES_TURNO_FIJO_INICIALES, fecha_inicio_vigencia: hoy });
    setAltaAbierta(true);
  };

  const cerrarAlta = () => {
    alta.limpiar();
    setAltaAbierta(false);
  };

  const bloquesAlta = useBloquesDeHorario({ canchaId: valores.cancha, diaSemana: valores.dia_semana, canchas });

  // Otra cancha u otro día cambian los bloques válidos: el horario elegido deja de valer.
  const cambiarValor = (campo, valor) => {
    alta.limpiar();
    setValores((actuales) => ({
      ...actuales,
      [campo]: valor,
      ...(campo === 'cancha' || campo === 'dia_semana' ? { hora_inicio: '' } : {}),
    }));
  };

  const registrar = async (evento) => {
    evento.preventDefault();
    setIntentado(true);
    if (Object.keys(erroresLocales).length > 0) return;
    const resultado = await alta.enviar(() => crearTurnoFijo(cuerpoTurnoFijo(valores)));
    if (!resultado.ok) return;
    setAltaAbierta(false);
    informar('turnosFijos.avisoAlta');
    recargarTodo();
  };

  // Pausar libera el horario; reanudar vuelve a validar choques en toda la vigencia y puede responder 409.
  const alternarPausa = async (turno) => {
    setAviso(null);
    setErrorAccion(null);
    setCambiando(turno.id);
    const reanudar = turno.estado === TURNO_FIJO_PAUSADO;
    try {
      await actualizarTurnoFijo(turno.id, { estado: reanudar ? TURNO_FIJO_VIGENTE : TURNO_FIJO_PAUSADO });
      informar(reanudar ? 'turnosFijos.avisoReanudado' : 'turnosFijos.avisoPausado');
    } catch (error) {
      setErrorAccion(error);
    } finally {
      setCambiando(null);
      recargarTodo();
    }
  };

  const baja = useConfirmacion((turno) => darDeBajaTurnoFijo(turno.id), {
    alExito: () => {
      informar('turnosFijos.avisoBaja');
      recargarTodo();
    },
    alError: (error) => {
      if (error.status === 404) recargarTodo();
    },
  });

  const [edicion, setEdicion] = useState(SIN_EDICION);
  const guardado = useEnvio();
  const bloquesEdicion = useBloquesDeHorario({
    canchaId: edicion.turno?.cancha ?? '',
    diaSemana: edicion.turno?.dia_semana ?? '',
    canchas,
  });

  const pedirEdicion = (turno) => {
    guardado.limpiar();
    setAviso(null);
    setEdicion({
      turno,
      hora_inicio: turno.hora_inicio.slice(0, 5),
      fecha_fin_vigencia: turno.fecha_fin_vigencia ?? '',
      conflicto: null,
    });
  };

  const cerrarEdicion = () => {
    guardado.limpiar();
    setEdicion(SIN_EDICION);
  };

  const guardarEdicion = async (confirmar = false) => {
    const cuerpo = cuerpoEdicion(edicion);
    if (Object.keys(cuerpo).length === 0) {
      cerrarEdicion();
      return;
    }
    const resultado = await guardado.enviar(() => actualizarTurnoFijo(
      edicion.turno.id,
      confirmar ? conConfirmacion(cuerpo) : cuerpo,
    ));
    if (resultado.ok) {
      cerrarEdicion();
      informar('turnosFijos.avisoActualizado');
      recargarTodo();
      return;
    }
    const conflicto = leerConflictos(resultado.error);
    if (conflicto && !confirmar) {
      guardado.limpiar();
      setEdicion((actual) => ({ ...actual, conflicto }));
    } else if (resultado.error.status === 404) {
      recargarTodo();
    }
  };

  const [fecha, setFecha] = useState(SIN_FECHA);
  const registroFecha = useEnvio();

  const pedirFecha = (turno) => {
    registroFecha.limpiar();
    setAviso(null);
    const [primera = ''] = proximasFechasDeTurnoFijo(turno, hoy, 1);
    setFecha({ turno, fecha: primera, accion: ACCION_FECHA_TURNO_FIJO.MANTENER });
  };

  const cerrarFecha = () => {
    registroFecha.limpiar();
    setFecha(SIN_FECHA);
  };

  const registrarFecha = async () => {
    const resultado = await registroFecha.enviar(() => registrarFechaTurnoFijo(fecha.turno.id, fecha.fecha, fecha.accion));
    if (!resultado.ok) {
      if (resultado.error.status === 404) recargarTodo();
      return;
    }
    cerrarFecha();
    informar('turnosFijos.avisoFecha');
    recargarTodo();
  };

  // Una fecha en espera se resuelve con la misma ruta: mantener la registra confirmada y cancelar, cancelada.
  const resolucion = useConfirmacion((pedido) => registrarFechaTurnoFijo(pedido.fila.turno.id, pedido.fila.fecha, pedido.accion), {
    alExito: (pedido) => {
      informar(pedido.accion === ACCION_FECHA_TURNO_FIJO.CANCELAR ? 'turnosFijos.avisoEsperaCancelada' : 'turnosFijos.avisoEsperaMantenida');
      recargarTodo();
    },
    alError: (error) => {
      if (error.status === 404 || error.status === 409) recargarTodo();
    },
  });

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
    alternarPausa,
    alta: {
      abierta: altaAbierta,
      valores,
      errores,
      error: alta.error,
      enviando: alta.enviando,
      hoy,
      bloques: bloquesAlta,
      abrir: abrirAlta,
      cerrar: cerrarAlta,
      cambiar: cambiarValor,
      enviar: registrar,
    },
    baja,
    edicion: {
      ...edicion,
      error: guardado.error,
      enviando: guardado.enviando,
      bloques: bloquesEdicion,
      pedir: pedirEdicion,
      cerrar: cerrarEdicion,
      cambiar: (campo, valor) => {
        guardado.limpiar();
        setEdicion((actual) => ({ ...actual, [campo]: valor }));
      },
      guardar: () => guardarEdicion(false),
      confirmar: () => guardarEdicion(true),
      volver: () => {
        guardado.limpiar();
        setEdicion((actual) => ({ ...actual, conflicto: null }));
      },
    },
    fecha: {
      ...fecha,
      opciones: fecha.turno ? proximasFechasDeTurnoFijo(fecha.turno, hoy, PARAMETROS.agenda.proximasFechas) : [],
      error: registroFecha.error,
      enviando: registroFecha.enviando,
      pedir: pedirFecha,
      cerrar: cerrarFecha,
      cambiar: (campo, valor) => {
        registroFecha.limpiar();
        setFecha((actual) => ({ ...actual, [campo]: valor }));
      },
      registrar: registrarFecha,
    },
    enEspera: {
      lista: { ...enEspera, items: aFilasEnEspera(enEspera.items) },
      turnos: enEspera.total,
      resolucion,
      pedirMantener: (fila) => resolucion.pedir({ fila, accion: ACCION_FECHA_TURNO_FIJO.MANTENER }),
      pedirCancelar: (fila) => resolucion.pedir({ fila, accion: ACCION_FECHA_TURNO_FIJO.CANCELAR }),
    },
  };
}
