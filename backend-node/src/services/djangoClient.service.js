import { obtenerParametros } from '../config/parametros.js';
import { ErrorHttp, ErrorServicioExterno } from '../middlewares/errores.middleware.js';

const ID_VALIDO = /^[1-9]\d*$/;
const MENSAJES_DE_ACCESO = {
  401: 'Debés iniciar sesión para acceder a este recurso.',
  403: 'No tenés permiso para realizar esta acción.',
  404: 'No se encontró el complejo.',
};

const ocultarTokens = (texto) => String(texto)
  .replace(/Bearer\s+\S+/g, 'Bearer ***')
  .replace(/eyJ[\w-]+\.[\w-]+\.[\w-]+/g, '***');

const falla = (causa) => {
  console.error('Django no respondió como se esperaba:', ocultarTokens(causa.message));
  return new ErrorServicioExterno('Django', causa);
};

// Acepta la URL con o sin `/api` y con o sin barra final.
const urlDeDjango = (ruta) => {
  const base = process.env.DJANGO_API_URL;
  if (!base) throw new Error('DJANGO_API_URL no está configurada en backend-node.');
  const sinBarra = base.replace(/\/+$/, '');
  return `${sinBarra.endsWith('/api') ? sinBarra : `${sinBarra}/api`}${ruta}`;
};

// El id se interpola en la ruta: solo un entero positivo, para que no se pueda pedir otra ruta de Django.
const rutaDeComplejo = (complejoId, sufijo = '') => {
  if (!ID_VALIDO.test(String(complejoId))) throw new Error(`complejoId inválido: ${complejoId}`);
  return `/complejos/${complejoId}/${sufijo}`;
};

const pedir = async (ruta, token) => {
  const url = urlDeDjango(ruta);
  try {
    return await fetch(url, {
      headers: { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      signal: AbortSignal.timeout(obtenerParametros().http.timeoutDjangoMs),
      // Una redirección podría reenviar el token a otra dirección: se trata como falla.
      redirect: 'error',
    });
  } catch (error) {
    throw falla(error);
  }
};

const leerJson = async (respuesta) => {
  try {
    return await respuesta.json();
  } catch (error) {
    throw falla(error);
  }
};

/** Datos públicos del complejo habilitado que usa Node (nombre y coordenadas), o `null` si no existe. */
export const obtenerComplejoPublico = async (complejoId) => {
  const respuesta = await pedir(rutaDeComplejo(complejoId));
  if (respuesta.status === 404) return null;
  if (!respuesta.ok) throw falla(new Error(`HTTP ${respuesta.status} en el detalle del complejo`));
  const datos = await leerJson(respuesta);
  return { id: datos.id, nombre: datos.nombre, latitud: Number(datos.latitud), longitud: Number(datos.longitud) };
};

/**
 * Confirma con Django que el usuario del token administra el complejo. Un 401, 403 o 404 de Django llega igual al
 * cliente, con el mensaje de Django; cualquier otra falla es un 502.
 */
export const verificarAccesoAComplejo = async (complejoId, token) => {
  const respuesta = await pedir(rutaDeComplejo(complejoId, 'acceso/'), token);
  if (respuesta.ok) return;
  if (respuesta.status in MENSAJES_DE_ACCESO) {
    const cuerpo = await respuesta.json().catch(() => ({}));
    const detalle = typeof cuerpo.detail === 'string' ? cuerpo.detail : MENSAJES_DE_ACCESO[respuesta.status];
    throw new ErrorHttp(respuesta.status, detalle);
  }
  throw falla(new Error(`HTTP ${respuesta.status} al verificar el acceso al complejo`));
};
