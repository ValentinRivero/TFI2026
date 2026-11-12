import { useState } from 'react';
import { t } from '../i18n/index.js';
import { listarTodosLosContratos } from '../services/contratoService.js';
import { actualizarUsuario, listarUsuarios, obtenerUsuario } from '../services/usuarioService.js';
import { cuerpoUsuario, FILTROS_USUARIOS_INICIALES, validarUsuario, valoresDeUsuario } from '../utils/sistema.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';
import useFiltrosAplicables from './useFiltrosAplicables.js';
import useListaPaginada from './useListaPaginada.js';

const SIN_FICHA = Object.freeze({ usuario: null, valores: null, editando: false });

/**
 * Cuentas de usuario (superadmin): lista paginada con filtros y ficha de cada cuenta. La ficha se abre en modo consulta
 * (solo lectura) y recién con "Habilitar edición" permite cambiar nombre, teléfono, rol, complejo operado y estado.
 * Las restricciones de negocio (último superadmin activo, dueño con contratos vigentes, operador sin complejo) las
 * valida el backend con `400` y su mensaje se muestra tal cual en la ficha, junto al campo afectado.
 *
 * `idInicial` abre la ficha de esa cuenta en modo consulta (enlace `?verUsuario=<id>` que llega desde la auditoría).
 */
export default function useUsuarios({ idInicial = null } = {}) {
  const filtros = useFiltrosAplicables(FILTROS_USUARIOS_INICIALES);
  const lista = useListaPaginada(
    (pagina, signal) => listarUsuarios(filtros.aplicados, pagina, signal),
    [filtros.aplicados],
  );

  const [aviso, setAviso] = useState(null);
  const [ficha, setFicha] = useState(SIN_FICHA);
  const [intentado, setIntentado] = useState(false);
  const [idAtendido, setIdAtendido] = useState(null);
  const guardado = useEnvio();

  // Ficha pedida por enlace: se consulta la cuenta y se abre una sola vez por id de la ruta.
  const deEnlace = useConsulta((signal) => (idInicial ? obtenerUsuario(idInicial, signal) : null), [idInicial]);
  if (idInicial === null && idAtendido !== null) {
    setIdAtendido(null);
  } else if (idInicial !== null && idAtendido !== idInicial && deEnlace.datos?.id === idInicial) {
    setIdAtendido(idInicial);
    setFicha({ usuario: deEnlace.datos, valores: valoresDeUsuario(deEnlace.datos), editando: false });
  }

  // Los complejos solo se necesitan al editar a un operador: se piden recién al abrir la ficha.
  const complejos = useConsulta(
    (signal) => (ficha.usuario ? listarTodosLosContratos(signal) : []),
    [Boolean(ficha.usuario)],
  );

  const erroresLocales = ficha.valores ? validarUsuario(ficha.valores) : {};
  const errores = { ...(intentado ? erroresLocales : {}), ...(guardado.error?.campos ?? {}) };

  const abrir = (usuario) => {
    guardado.limpiar();
    setIntentado(false);
    setAviso(null);
    setFicha({ usuario, valores: valoresDeUsuario(usuario), editando: false });
  };

  const cerrar = () => {
    guardado.limpiar();
    setFicha(SIN_FICHA);
  };

  const habilitarEdicion = () => setFicha((actual) => ({ ...actual, editando: true }));

  // Cancelar la edición vuelve a la consulta con los datos guardados, sin enviar nada.
  const cancelarEdicion = () => {
    guardado.limpiar();
    setIntentado(false);
    setFicha((actual) => ({ ...actual, valores: valoresDeUsuario(actual.usuario), editando: false }));
  };

  const cambiar = (campo, valor) => {
    guardado.limpiar();
    setFicha((actual) => ({ ...actual, valores: { ...actual.valores, [campo]: valor } }));
  };

  const guardar = async (evento) => {
    evento?.preventDefault();
    setIntentado(true);
    if (Object.keys(erroresLocales).length > 0) return;
    const cuerpo = cuerpoUsuario(ficha.valores, ficha.usuario);
    if (Object.keys(cuerpo).length === 0) {
      cancelarEdicion();
      return;
    }
    const resultado = await guardado.enviar(() => actualizarUsuario(ficha.usuario.id, cuerpo));
    if (!resultado.ok) {
      if (resultado.error.status === 404) lista.recargar();
      return;
    }
    setFicha((actual) => ({ ...actual, usuario: resultado.resultado, valores: valoresDeUsuario(resultado.resultado), editando: false }));
    setAviso(t('usuarios.avisoGuardado'));
    lista.recargar();
  };

  return {
    lista,
    filtros,
    aviso,
    descartarAviso: () => setAviso(null),
    errorFicha: idInicial !== null && !deEnlace.cargando ? deEnlace.error : null,
    ficha: {
      ...ficha,
      errores,
      error: guardado.error,
      enviando: guardado.enviando,
      complejos: complejos.datos ?? [],
      abrir,
      cerrar,
      habilitarEdicion,
      cancelarEdicion,
      cambiar,
      guardar,
    },
  };
}
