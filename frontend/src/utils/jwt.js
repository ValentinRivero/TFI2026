/**
 * Decodificación del payload de un JWT, solo para leer datos de navegación (`rol`, `usuario_id`). No verifica la
 * firma: la autoridad real son los backends, que validan cada petición.
 */
const decodificarBase64Url = (texto) => {
  const base64 = texto.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(texto.length / 4) * 4, '=');
  const binario = atob(base64);
  const bytes = Uint8Array.from(binario, (caracter) => caracter.charCodeAt(0));
  return new TextDecoder().decode(bytes);
};

/** Payload del token como objeto, o `null` si no tiene la forma de un JWT. */
export const decodificarJwt = (token) => {
  if (typeof token !== 'string') return null;
  const partes = token.split('.');
  if (partes.length !== 3 || !partes[1]) return null;
  try {
    const payload = JSON.parse(decodificarBase64Url(partes[1]));
    return payload !== null && typeof payload === 'object' && !Array.isArray(payload) ? payload : null;
  } catch {
    return null;
  }
};

/** `{ usuarioId, rol, expira }` de un access token; `usuarioId` es numérico (SimpleJWT lo emite como texto). */
export const datosDeAccess = (token) => {
  const payload = decodificarJwt(token);
  if (!payload) return null;
  const usuarioId = Number(payload.usuario_id);
  return {
    usuarioId: Number.isInteger(usuarioId) && usuarioId > 0 ? usuarioId : null,
    rol: typeof payload.rol === 'string' && payload.rol ? payload.rol : null,
    expira: typeof payload.exp === 'number' ? payload.exp : null,
  };
};
