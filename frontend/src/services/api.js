/**
 * Capa de red: las dos instancias de Axios (Django y Node) con sus interceptores. Es el único módulo que conoce las
 * URLs de los backends; las páginas nunca las ven. Archivo protegido (CLAUDE.md §3): solo ediciones quirúrgicas.
 *
 * - Request: inyecta `Authorization: Bearer <access>` con el access en memoria. Las rutas de sesión
 *   (`/api/token/...`) viajan sin ese encabezado y con `withCredentials`, porque la cookie HttpOnly del refresh es la
 *   única que se envía y solo a esas rutas. `apiNode` nunca envía credenciales.
 * - Response: ante un 401 con sesión, pide un access nuevo a `POST /api/token/refresh/` (una única promesa compartida
 *   por todas las peticiones simultáneas) y reintenta una sola vez. Si el refresh falla, limpia la sesión en memoria.
 * - Errores: todo error se entrega como `ErrorApi` (ver `utils/errores.js`).
 */
import axios from 'axios';
import { ENTORNO, PARAMETROS } from '../config/parametros.js';
import { normalizarError } from '../utils/errores.js';

const RUTA_DE_SESION = '/api/token/';
const RUTA_DE_REFRESH = '/api/token/refresh/';

const esRutaDeSesion = (url) => typeof url === 'string' && url.startsWith(RUTA_DE_SESION);

// `authService` registra acá cómo leer, guardar y limpiar el access. Así `api.js` no depende de él.
let gestorDeSesion = {
  obtenerAccess: () => null,
  guardarAccess: () => {},
  limpiarSesion: () => {},
};

export const registrarGestorDeSesion = (gestor) => {
  gestorDeSesion = { ...gestorDeSesion, ...gestor };
};

export const apiDjango = axios.create({ baseURL: ENTORNO.urlDjango, timeout: PARAMETROS.http.timeoutDjangoMs });
export const apiNode = axios.create({ baseURL: ENTORNO.urlNode, timeout: PARAMETROS.http.timeoutNodeMs, withCredentials: false });

const agregarCredenciales = (config) => {
  const access = gestorDeSesion.obtenerAccess();
  const deSesion = esRutaDeSesion(config.url);
  if (access && !deSesion) config.headers.Authorization = `Bearer ${access}`;
  if (config.baseURL === ENTORNO.urlDjango) config.withCredentials = deSesion;
  return config;
};

apiDjango.interceptors.request.use(agregarCredenciales);
apiNode.interceptors.request.use(agregarCredenciales);

let renovacionEnCurso = null;

/**
 * Pide un access nuevo con la cookie del refresh. Varias llamadas simultáneas comparten la misma promesa: el refresh
 * rota la cookie y pedirlo en paralelo haría fallar a las demás. Si falla, la sesión en memoria se limpia.
 */
export const renovarAccess = () => {
  if (!renovacionEnCurso) {
    renovacionEnCurso = apiDjango
      .post(RUTA_DE_REFRESH)
      .then(({ data }) => {
        gestorDeSesion.guardarAccess(data.access);
        return data.access;
      })
      .catch((error) => {
        gestorDeSesion.limpiarSesion();
        throw error;
      })
      .finally(() => {
        renovacionEnCurso = null;
      });
  }
  return renovacionEnCurso;
};

const manejarError = async (error) => {
  if (error?.code === 'ERR_CANCELED') throw error;

  const original = error?.config;
  const conSesion = Boolean(original?.headers?.Authorization);
  if (error?.response?.status === 401 && original && conSesion && !original._reintentado && !esRutaDeSesion(original.url)) {
    original._reintentado = true;
    let access;
    try {
      access = await renovarAccess();
    } catch {
      // Sin refresh válido la sesión ya se limpió: se informa el 401 original.
      throw normalizarError(error);
    }
    original.headers.Authorization = `Bearer ${access}`;
    // El reintento pasa por los mismos interceptores, así que su error ya llega normalizado.
    return (original.baseURL === ENTORNO.urlNode ? apiNode : apiDjango)(original);
  }
  throw normalizarError(error);
};

apiDjango.interceptors.response.use((respuesta) => respuesta, manejarError);
apiNode.interceptors.response.use((respuesta) => respuesta, manejarError);
