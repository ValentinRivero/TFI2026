import { ROL } from '../config/catalogos.js';
import { PARAMETROS } from '../config/parametros.js';
import { t } from '../i18n/index.js';
import { validarConfiguracion } from './complejo.js';
import { parsearFecha } from './formatos.js';

const aTexto = (valor) => (valor === null || valor === undefined ? '' : String(valor));

/** Parámetros comunes de los listados del sistema: la página y solo los filtros con valor. */
const sinVacios = (params) => Object.fromEntries(Object.entries(params).filter(([, valor]) => valor !== '' && valor !== null));

// Contratos

export const FILTROS_CONTRATOS_INICIALES = Object.freeze({ estado: '', busqueda: '', orden: 'nombre' });

/** Parámetros de `GET /api/contratos/` con los filtros y la página. */
export const aParametrosContratos = (filtros, pagina) => sinVacios({
  page: pagina,
  estado_contrato: filtros.estado,
  search: filtros.busqueda.trim(),
  ordering: filtros.orden,
});

export const VALORES_COMPLEJO_NUEVO_INICIALES = Object.freeze({
  propietario: '',
  nombre: '',
  direccion: '',
  latitud: '',
  longitud: '',
  telefono_contacto: '',
  horas_limite_cancelacion: String(PARAMETROS.panel.horasCancelacionDefecto),
  info_sena: '',
  estado_contrato: '1',
});

/** Errores por campo del alta de un complejo con su contrato; reutiliza las reglas de la configuración del complejo. */
export const validarComplejoNuevo = (valores) => {
  const errores = validarConfiguracion(valores);
  if (!valores.propietario) errores.propietario = t('contratos.errorPropietario');
  return errores;
};

/** Cuerpo del `POST /api/contratos/`; los campos opcionales vacíos no viajan y el backend usa su valor por defecto. */
export const cuerpoComplejoNuevo = (valores) => {
  const cuerpo = {
    propietario: Number(valores.propietario),
    nombre: valores.nombre.trim(),
    direccion: valores.direccion.trim(),
    latitud: valores.latitud.trim(),
    longitud: valores.longitud.trim(),
    horas_limite_cancelacion: Number(valores.horas_limite_cancelacion),
    estado_contrato: Number(valores.estado_contrato),
  };
  if (valores.telefono_contacto.trim()) cuerpo.telefono_contacto = valores.telefono_contacto.trim();
  if (valores.info_sena.trim()) cuerpo.info_sena = valores.info_sena.trim();
  return cuerpo;
};

// Usuarios

/** Id de usuario de un parámetro de la ruta (`?verUsuario=`): un entero positivo, o `null` si falta o es inválido. */
export const idDeUsuarioEnRuta = (texto) => (/^[1-9]\d{0,9}$/.test(texto ?? '') ? Number(texto) : null);

export const FILTROS_USUARIOS_INICIALES = Object.freeze({ rol: '', estado: '', busqueda: '' });

/** Parámetros de `GET /api/usuarios/` con los filtros y la página. */
export const aParametrosUsuarios = (filtros, pagina) => sinVacios({
  page: pagina,
  rol: filtros.rol,
  estado: filtros.estado,
  search: filtros.busqueda.trim(),
});

/** Valores del formulario de edición de una cuenta (siempre texto, como los entrega un control). */
export const valoresDeUsuario = (usuario) => ({
  nombre_completo: aTexto(usuario.nombre_completo),
  telefono: aTexto(usuario.telefono),
  rol: aTexto(usuario.rol),
  complejo_operado: aTexto(usuario.complejo_operado),
  estado: aTexto(usuario.estado),
});

export const validarUsuario = (valores) => {
  const errores = {};
  if (valores.nombre_completo.trim() === '') errores.nombre_completo = t('usuarios.errorNombre');
  return errores;
};

/**
 * Cuerpo del `PATCH /api/usuarios/<id>/` con solo los campos que cambiaron. El complejo operado viaja únicamente si
 * el rol final es operador: con otro rol el backend lo deja vacío y rechaza uno asignado.
 */
export const cuerpoUsuario = (valores, original) => {
  const cuerpo = {};
  const nombre = valores.nombre_completo.trim();
  if (nombre !== aTexto(original.nombre_completo).trim()) cuerpo.nombre_completo = nombre;
  const telefono = valores.telefono.trim();
  if (telefono !== aTexto(original.telefono).trim()) cuerpo.telefono = telefono;
  if (valores.rol !== original.rol) cuerpo.rol = valores.rol;
  if (valores.estado !== aTexto(original.estado)) cuerpo.estado = Number(valores.estado);
  if (valores.rol === ROL.OPERADOR && valores.complejo_operado !== aTexto(original.complejo_operado)) {
    cuerpo.complejo_operado = valores.complejo_operado === '' ? null : Number(valores.complejo_operado);
  }
  return cuerpo;
};

// Auditoría

export const FILTROS_AUDITORIA_INICIALES = Object.freeze({
  tipo_evento: '',
  usuario: '',
  complejo: '',
  ip_origen: '',
  fecha_desde: '',
  fecha_hasta: '',
});

const IPV4 = /^(\d{1,3})(\.\d{1,3}){3}$/;
const IPV6 = /^[0-9a-f:]+$/i;

/** Una IP con forma de IPv4 o IPv6; el backend valida el detalle y responde 400 ante una inválida. */
export const esDireccionIp = (texto) => {
  const valor = texto.trim();
  if (IPV4.test(valor)) return valor.split('.').every((parte) => Number(parte) <= 255);
  return valor.includes(':') && IPV6.test(valor);
};

/** Errores por campo de los filtros de auditoría; un objeto vacío significa que se pueden aplicar. */
export const validarFiltrosAuditoria = (filtros) => {
  const errores = {};
  if (filtros.usuario.trim() !== '' && !/^[1-9]\d*$/.test(filtros.usuario.trim())) errores.usuario = t('auditoria.errorUsuario');
  if (filtros.ip_origen.trim() !== '' && !esDireccionIp(filtros.ip_origen)) errores.ip_origen = t('auditoria.errorIp');
  if (filtros.fecha_desde && !parsearFecha(filtros.fecha_desde)) errores.fecha_desde = t('auditoria.errorFecha');
  if (filtros.fecha_hasta && !parsearFecha(filtros.fecha_hasta)) errores.fecha_hasta = t('auditoria.errorFecha');
  if (!errores.fecha_desde && !errores.fecha_hasta && filtros.fecha_desde && filtros.fecha_hasta
    && filtros.fecha_hasta < filtros.fecha_desde) {
    errores.fecha_hasta = t('auditoria.errorOrden');
  }
  return errores;
};

/** Parámetros de `GET /api/auditoria/` con los filtros y la página. */
export const aParametrosAuditoria = (filtros, pagina) => sinVacios({
  page: pagina,
  tipo_evento: filtros.tipo_evento,
  usuario: filtros.usuario.trim(),
  complejo: filtros.complejo,
  ip_origen: filtros.ip_origen.trim(),
  fecha_desde: filtros.fecha_desde,
  fecha_hasta: filtros.fecha_hasta,
});
