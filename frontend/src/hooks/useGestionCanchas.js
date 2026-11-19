import { useState } from 'react';
import { t } from '../i18n/index.js';
import { actualizarCancha, crearCancha, darDeBajaCancha, listarCanchas } from '../services/canchaService.js';
import { listarDeportes } from '../services/complejoService.js';
import { cuerpoCancha, validarCancha, valoresDeCancha, VALORES_CANCHA_INICIALES } from '../utils/canchaAdmin.js';
import { conConfirmacion, leerConflictos } from '../utils/conflictos.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';
import useListaPaginada from './useListaPaginada.js';

const SIN_FORMULARIO = Object.freeze({ abierto: false, cancha: null, valores: VALORES_CANCHA_INICIALES });

/**
 * Canchas del complejo activo: lista paginada, alta y edición en un formulario, baja lógica con confirmación y
 * conflictos que piden confirmar (cambio de duración o paso a mantenimiento con reservas futuras).
 *
 * Cuando el servidor responde 409 con `requiere_confirmacion`, el formulario se oculta, `conflicto` pasa a tener el
 * detalle y `confirmarConflicto` repite el mismo cambio con `confirmar: true`. Si el usuario cancela, el formulario
 * vuelve a mostrarse con lo que había escrito.
 */
export default function useGestionCanchas(complejoId) {
  const lista = useListaPaginada((pagina, signal) => listarCanchas(complejoId, pagina, signal), [complejoId]);
  const deportes = useConsulta((signal) => listarDeportes(signal), []);
  const [formulario, setFormulario] = useState(SIN_FORMULARIO);
  const [intentado, setIntentado] = useState(false);
  const [conflicto, setConflicto] = useState(null);
  const [aBaja, setABaja] = useState(null);
  const [aviso, setAviso] = useState(null);
  const guardado = useEnvio();
  const baja = useEnvio();

  const abrirAlta = () => {
    guardado.limpiar();
    setIntentado(false);
    setAviso(null);
    setFormulario({ abierto: true, cancha: null, valores: VALORES_CANCHA_INICIALES });
  };

  const abrirEdicion = (cancha) => {
    guardado.limpiar();
    setIntentado(false);
    setAviso(null);
    setFormulario({ abierto: true, cancha, valores: valoresDeCancha(cancha) });
  };

  const cerrarFormulario = () => {
    guardado.limpiar();
    setConflicto(null);
    setFormulario(SIN_FORMULARIO);
  };

  const cambiar = (campo, valor) => {
    guardado.limpiar();
    setFormulario((actual) => ({ ...actual, valores: { ...actual.valores, [campo]: valor } }));
  };

  const cuerpoActual = () => cuerpoCancha(formulario.valores, { complejoId, original: formulario.cancha });
  const erroresLocales = validarCancha(formulario.valores);
  const errores = { ...(intentado ? erroresLocales : {}), ...(guardado.error?.campos ?? {}) };

  const terminar = (editando) => {
    setConflicto(null);
    setFormulario(SIN_FORMULARIO);
    setAviso(t(editando ? 'gestionCanchas.actualizada' : 'gestionCanchas.creada'));
    lista.recargar();
  };

  const guardar = async (confirmar = false) => {
    const editando = Boolean(formulario.cancha);
    const cuerpo = cuerpoActual();
    if (editando && Object.keys(cuerpo).length === 0) {
      cerrarFormulario();
      return;
    }
    const resultado = await guardado.enviar(() => (
      editando
        ? actualizarCancha(formulario.cancha.id, confirmar ? conConfirmacion(cuerpo) : cuerpo)
        : crearCancha(cuerpo)
    ));
    if (resultado.ok) {
      terminar(editando);
      return;
    }
    const detalle = leerConflictos(resultado.error);
    if (detalle) {
      guardado.limpiar();
      setConflicto(detalle);
    }
  };

  const enviar = async (evento) => {
    evento.preventDefault();
    setIntentado(true);
    if (Object.keys(erroresLocales).length > 0) return;
    await guardar(false);
  };

  const pedirBaja = (cancha) => {
    baja.limpiar();
    setAviso(null);
    setABaja(cancha);
  };

  const cerrarBaja = () => {
    baja.limpiar();
    setABaja(null);
  };

  const confirmarBaja = async () => {
    if (!aBaja) return;
    const resultado = await baja.enviar(() => darDeBajaCancha(aBaja.id));
    if (!resultado.ok) {
      if (resultado.error.status === 404) lista.recargar();
      return;
    }
    setABaja(null);
    setAviso(t('gestionCanchas.baja'));
    lista.recargar();
  };

  return {
    lista,
    deportes: deportes.datos ?? [],
    formulario: {
      abierto: formulario.abierto && !conflicto,
      editando: Boolean(formulario.cancha),
      valores: formulario.valores,
      errores,
      error: guardado.error,
      enviando: guardado.enviando,
      cambiar,
      enviar,
      cerrar: cerrarFormulario,
    },
    abrirAlta,
    abrirEdicion,
    conflicto: conflicto && { ...conflicto, error: guardado.error },
    confirmarConflicto: () => guardar(true),
    cancelarConflicto: () => setConflicto(null),
    baja: { cancha: aBaja, error: baja.error, pedir: pedirBaja, cerrar: cerrarBaja, confirmar: confirmarBaja },
    aviso,
    descartarAviso: () => setAviso(null),
  };
}
