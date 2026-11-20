import { useState } from 'react';
import { t } from '../i18n/index.js';
import {
  actualizarRol,
  crearRol,
  darDeBajaRol,
  listarPermisos,
  listarRoles,
  reactivarRol,
} from '../services/rolService.js';
import { FILTROS_CATALOGO_INICIALES, hayFiltroActivo } from '../utils/catalogoSistema.js';
import {
  alternarPermiso,
  cuerpoRolEdicion,
  cuerpoRolNuevo,
  filtrarRoles,
  validarRol,
  VALORES_ROL_INICIALES,
  valoresDeRol,
} from '../utils/roles.js';
import useConfirmacion from './useConfirmacion.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';
import useFiltros from './useFiltros.js';

const FORMULARIO_CERRADO = Object.freeze({ abierto: false, rol: null, valores: VALORES_ROL_INICIALES, intentado: false });

/**
 * Roles del superadmin: lista completa con sus bajas, permisos y usos; alta y edición de roles personalizados con un
 * selector de permisos; baja lógica con confirmación y reactivación; y una ficha de solo lectura con los permisos de
 * cualquier rol (también de los base, que son de solo lectura). La lista se filtra en el cliente por nombre o
 * descripción y por estado. El backend rechaza la baja de un rol en uso y los
 * permisos exclusivos de la plataforma con su motivo, que se muestra tal cual.
 */
export default function useRolesSistema() {
  const consulta = useConsulta((signal) => listarRoles(signal), []);
  const permisos = useConsulta((signal) => listarPermisos(signal), []);
  const [aviso, setAviso] = useState(null);
  const [formulario, setFormulario] = useState(FORMULARIO_CERRADO);
  const [ficha, setFicha] = useState(null);
  const guardado = useEnvio();
  const reactivacion = useEnvio();

  const busqueda = useFiltros(FILTROS_CATALOGO_INICIALES);

  const todos = consulta.datos ?? [];
  const items = filtrarRoles(todos, busqueda.filtros);
  const lista = {
    items,
    total: items.length,
    paginas: 1,
    pagina: 1,
    irAPagina: () => {},
    cargando: consulta.cargando && consulta.datos === null,
    error: consulta.error,
    recargar: consulta.recargar,
  };

  const baja = useConfirmacion((rol) => darDeBajaRol(rol.id), {
    alExito: (rol) => {
      setAviso(t('roles.avisoBaja', { nombre: rol.nombre }));
      consulta.recargar();
    },
    alError: (error) => {
      if (error.status === 404) consulta.recargar();
    },
  });

  const abrir = (rol) => {
    guardado.limpiar();
    setAviso(null);
    setFormulario({
      abierto: true,
      rol,
      valores: rol ? valoresDeRol(rol) : VALORES_ROL_INICIALES,
      intentado: false,
    });
  };

  const cerrar = () => {
    guardado.limpiar();
    setFormulario(FORMULARIO_CERRADO);
  };

  const cambiar = (campo, valor) => {
    guardado.limpiar();
    setFormulario((actual) => ({ ...actual, valores: { ...actual.valores, [campo]: valor } }));
  };

  const alternar = (permisoId) => {
    guardado.limpiar();
    setFormulario((actual) => ({
      ...actual,
      valores: { ...actual.valores, permisos: alternarPermiso(actual.valores.permisos, permisoId) },
    }));
  };

  const erroresLocales = validarRol(formulario.valores);
  const errores = {
    ...(formulario.intentado ? erroresLocales : {}),
    ...(guardado.error?.campos ?? {}),
  };

  const guardar = async (evento) => {
    evento?.preventDefault();
    setFormulario((actual) => ({ ...actual, intentado: true }));
    if (Object.keys(erroresLocales).length > 0) return;
    const { rol, valores } = formulario;
    const cuerpo = rol ? cuerpoRolEdicion(valores, rol) : cuerpoRolNuevo(valores);
    if (rol && Object.keys(cuerpo).length === 0) {
      cerrar();
      return;
    }
    const resultado = await guardado.enviar(() => (rol ? actualizarRol(rol.id, cuerpo) : crearRol(cuerpo)));
    if (!resultado.ok) {
      if (resultado.error.status === 404) consulta.recargar();
      return;
    }
    cerrar();
    setAviso(t(rol ? 'roles.avisoEdicion' : 'roles.avisoAlta', { nombre: resultado.resultado.nombre }));
    consulta.recargar();
  };

  const reactivar = async (rol) => {
    setAviso(null);
    const resultado = await reactivacion.enviar(() => reactivarRol(rol.id));
    if (!resultado.ok) {
      if (resultado.error.status === 404) consulta.recargar();
      return;
    }
    setAviso(t('roles.avisoReactivacion', { nombre: rol.nombre }));
    consulta.recargar();
  };

  return {
    lista,
    hayItems: todos.length > 0,
    filtros: {
      valores: busqueda.filtros,
      activos: hayFiltroActivo(busqueda.filtros),
      cambiar: busqueda.cambiar,
      limpiar: busqueda.limpiar,
    },
    aviso,
    descartarAviso: () => setAviso(null),
    errorReactivacion: reactivacion.error,
    descartarErrorReactivacion: reactivacion.limpiar,
    reactivar,
    baja,
    permisos: {
      items: permisos.datos ?? [],
      cargando: permisos.cargando && permisos.datos === null,
      error: permisos.error,
      recargar: permisos.recargar,
    },
    ficha: { rol: ficha, abrir: setFicha, cerrar: () => setFicha(null) },
    formulario: {
      ...formulario,
      editando: formulario.rol !== null,
      errores,
      error: guardado.error,
      enviando: guardado.enviando,
      abrir,
      cerrar,
      cambiar,
      alternar,
      guardar,
    },
  };
}
