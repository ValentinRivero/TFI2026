/**
 * Sesión del usuario. El access token vive solo en memoria de este módulo: nunca en `localStorage` ni
 * `sessionStorage`, así un script inyectado no puede leerlo de ahí. El refresh viaja en una cookie HttpOnly que
 * JavaScript no ve. Al recargar la página la sesión se recupera pidiendo un access nuevo con esa cookie.
 *
 * El estado se publica con `suscribir` y `obtenerEstado` (para `useSyncExternalStore`); cada cambio crea un objeto
 * nuevo, así el snapshot es estable entre cambios.
 */
import { datosDeAccess } from '../utils/jwt.js';
import { apiDjango, registrarGestorDeSesion, renovarAccess } from './api.js';

const ESTADO_INICIAL = Object.freeze({
  access: null,
  usuarioId: null,
  rol: null,
  perfil: null,
  cargandoSesion: true,
});

let estado = ESTADO_INICIAL;
const oyentes = new Set();

const publicar = (cambios) => {
  estado = Object.freeze({ ...estado, ...cambios });
  oyentes.forEach((avisar) => avisar());
};

export const suscribir = (oyente) => {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
};

export const obtenerEstado = () => estado;

const guardarAccess = (access) => {
  const datos = datosDeAccess(access);
  publicar({ access, usuarioId: datos?.usuarioId ?? null, rol: datos?.rol ?? null });
};

const limpiarSesion = () => {
  publicar({ access: null, usuarioId: null, rol: null, perfil: null });
};

registrarGestorDeSesion({
  obtenerAccess: () => estado.access,
  guardarAccess,
  limpiarSesion,
});

export const obtenerPerfil = async () => {
  const { data } = await apiDjango.get('/api/perfil/');
  publicar({ perfil: data });
  return data;
};

export const actualizarPerfil = async (cambios) => {
  const { data } = await apiDjango.patch('/api/perfil/', cambios);
  publicar({ perfil: data });
  return data;
};

/**
 * Recupera la sesión al abrir la app: un refresh con la cookie y, si resulta, el perfil. Sin sesión previa termina en
 * silencio como anónimo. Se ejecuta una sola vez aunque se llame varias.
 */
let inicio = null;
export const iniciarSesionPrevia = () => {
  if (!inicio) {
    inicio = renovarAccess()
      .then(() => obtenerPerfil())
      .catch(() => limpiarSesion())
      .finally(() => publicar({ cargandoSesion: false }));
  }
  return inicio;
};

export const login = async (email, password) => {
  const { data } = await apiDjango.post('/api/token/', { email, password });
  guardarAccess(data.access);
  try {
    return await obtenerPerfil();
  } catch (error) {
    limpiarSesion();
    throw error;
  }
};

/** Cierra la sesión en el servidor (revoca el refresh) y en memoria. Un fallo de red no deja la sesión abierta. */
export const logout = async () => {
  try {
    await apiDjango.post('/api/token/logout/');
  } catch {
    // El refresh vence solo; lo importante es que el navegador quede sin sesión.
  } finally {
    limpiarSesion();
  }
};

export const registrar = async (datos) => {
  const { data } = await apiDjango.post('/api/registro/', datos);
  return data;
};
