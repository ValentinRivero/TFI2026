import { useState } from 'react';
import { t } from '../i18n/index.js';
import {
  crearItemCatalogo,
  darDeBajaItemCatalogo,
  listarCatalogoSistema,
  reactivarItemCatalogo,
  renombrarItemCatalogo,
} from '../services/catalogoSistemaService.js';
import { normalizarNombre, validarNombreCatalogo } from '../utils/catalogoSistema.js';
import useConfirmacion from './useConfirmacion.js';
import useConsulta from './useConsulta.js';
import useEnvio from './useEnvio.js';

const FORMULARIO_CERRADO = Object.freeze({ abierto: false, item: null, nombre: '', intentado: false });

/**
 * Catálogo maestro (deportes o servicios) del superadmin: lista completa con sus bajas y usos, alta, cambio de nombre,
 * baja lógica con confirmación y reactivación. `recurso` es una clave de `CATALOGOS_SISTEMA`. El backend rechaza la
 * baja de un ítem en uso con su motivo, que queda dentro del diálogo de confirmación.
 */
export default function useCatalogoSistema(recurso) {
  const consulta = useConsulta((signal) => listarCatalogoSistema(recurso, signal), [recurso]);
  const [aviso, setAviso] = useState(null);
  const [formulario, setFormulario] = useState(FORMULARIO_CERRADO);
  const guardado = useEnvio();
  const reactivacion = useEnvio();

  const items = consulta.datos ?? [];
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

  const baja = useConfirmacion((item) => darDeBajaItemCatalogo(recurso, item.id), {
    alExito: (item) => {
      setAviso(t('catalogoSistema.avisoBaja', { nombre: item.nombre }));
      consulta.recargar();
    },
    alError: (error) => {
      if (error.status === 404) consulta.recargar();
    },
  });

  const abrir = (item) => {
    guardado.limpiar();
    setAviso(null);
    setFormulario({ abierto: true, item, nombre: item?.nombre ?? '', intentado: false });
  };

  const cerrar = () => {
    guardado.limpiar();
    setFormulario(FORMULARIO_CERRADO);
  };

  const cambiarNombre = (nombre) => {
    guardado.limpiar();
    setFormulario((actual) => ({ ...actual, nombre }));
  };

  const errorLocal = validarNombreCatalogo(formulario.nombre, recurso);
  const errores = {
    ...(formulario.intentado && errorLocal ? { nombre: errorLocal } : {}),
    ...(guardado.error?.campos ?? {}),
  };

  const guardar = async (evento) => {
    evento?.preventDefault();
    setFormulario((actual) => ({ ...actual, intentado: true }));
    if (errorLocal) return;
    const nombre = normalizarNombre(formulario.nombre);
    const { item } = formulario;
    if (item && nombre === item.nombre) {
      cerrar();
      return;
    }
    const resultado = await guardado.enviar(
      () => (item ? renombrarItemCatalogo(recurso, item.id, nombre) : crearItemCatalogo(recurso, nombre)),
    );
    if (!resultado.ok) {
      if (resultado.error.status === 404) consulta.recargar();
      return;
    }
    cerrar();
    setAviso(t(item ? 'catalogoSistema.avisoEdicion' : 'catalogoSistema.avisoAlta', { nombre }));
    consulta.recargar();
  };

  const reactivar = async (item) => {
    setAviso(null);
    const resultado = await reactivacion.enviar(() => reactivarItemCatalogo(recurso, item.id));
    if (!resultado.ok) {
      if (resultado.error.status === 404) consulta.recargar();
      return;
    }
    setAviso(t('catalogoSistema.avisoReactivacion', { nombre: item.nombre }));
    consulta.recargar();
  };

  return {
    lista,
    aviso,
    descartarAviso: () => setAviso(null),
    errorReactivacion: reactivacion.error,
    descartarErrorReactivacion: reactivacion.limpiar,
    reactivar,
    baja,
    formulario: {
      ...formulario,
      editando: formulario.item !== null,
      errores,
      error: guardado.error,
      enviando: guardado.enviando,
      abrir,
      cerrar,
      cambiarNombre,
      guardar,
    },
  };
}
