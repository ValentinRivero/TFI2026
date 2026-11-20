import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { normalizarNombre } from './catalogoSistema.js';

const { limitesCampos, cuenta } = PARAMETROS;

export const VALORES_ROL_INICIALES = Object.freeze({ nombre: '', descripcion: '', permisos: Object.freeze([]) });

/** Valores del formulario con los datos de un rol: los permisos viajan como ids. */
export const valoresDeRol = (rol) => ({
  nombre: rol.nombre,
  descripcion: rol.descripcion ?? '',
  permisos: rol.permisos.map((permiso) => permiso.id),
});

/** Errores por campo del formulario de un rol; un objeto vacío significa que se puede enviar. */
export const validarRol = (valores) => {
  const errores = {};
  const nombre = normalizarNombre(valores.nombre);
  if (nombre === '') errores.nombre = t('catalogoSistema.errorNombreVacio');
  else if (nombre.length < cuenta.nombreLargoMinimo) {
    errores.nombre = t('catalogoSistema.errorNombreCorto', { minimo: cuenta.nombreLargoMinimo });
  } else if (nombre.length > limitesCampos.nombreRol) {
    errores.nombre = t('catalogoSistema.errorNombreLargo', { maximo: limitesCampos.nombreRol });
  }
  if (valores.descripcion.trim().length > limitesCampos.descripcionRol) {
    errores.descripcion = t('roles.errorDescripcion', { maximo: limitesCampos.descripcionRol });
  }
  return errores;
};

/** Agrega el permiso a la selección o lo quita si ya estaba. */
export const alternarPermiso = (seleccionados, permisoId) => (
  seleccionados.includes(permisoId)
    ? seleccionados.filter((id) => id !== permisoId)
    : [...seleccionados, permisoId]
);

const mismosIds = (a, b) => a.length === b.length && a.every((id) => b.includes(id));

/** Cuerpo del `POST /api/sistema/roles/`: la descripción vacía no viaja. */
export const cuerpoRolNuevo = (valores) => {
  const cuerpo = { nombre: normalizarNombre(valores.nombre), permisos: [...valores.permisos] };
  const descripcion = valores.descripcion.trim();
  if (descripcion) cuerpo.descripcion = descripcion;
  return cuerpo;
};

/** Cuerpo del `PATCH` con solo lo que cambió respecto del rol guardado; `permisos` reemplaza la lista completa. */
export const cuerpoRolEdicion = (valores, rol) => {
  const cuerpo = {};
  const nombre = normalizarNombre(valores.nombre);
  if (nombre !== rol.nombre) cuerpo.nombre = nombre;
  const descripcion = valores.descripcion.trim();
  if (descripcion !== (rol.descripcion ?? '')) cuerpo.descripcion = descripcion;
  const idsActuales = rol.permisos.map((permiso) => permiso.id);
  if (!mismosIds(valores.permisos, idsActuales)) cuerpo.permisos = [...valores.permisos];
  return cuerpo;
};

/** Permisos agrupados por módulo, en el orden en que llegan: `[{ modulo, permisos: [...] }]`. */
export const agruparPermisosPorModulo = (permisos) => {
  const grupos = new Map();
  permisos.forEach((permiso) => {
    if (!grupos.has(permiso.modulo)) grupos.set(permiso.modulo, []);
    grupos.get(permiso.modulo).push(permiso);
  });
  return [...grupos].map(([modulo, delModulo]) => ({ modulo, permisos: delModulo }));
};

/** Un rol protegido de la carga inicial no se edita ni se da de baja. */
export const esRolEditable = (rol) => !rol.es_base;
