import jwt from 'jsonwebtoken';

const MENSAJE_SIN_SESION = 'Debés iniciar sesión para acceder a este recurso.';
const MENSAJE_TOKEN_INVALIDO = 'El token es inválido o expiró.';

const rechazar = (res, mensaje) => res
  .status(401)
  .set('WWW-Authenticate', 'Bearer realm="api"')
  .json({ error: true, mensaje });

const leerToken = (encabezado) => {
  if (!encabezado) return { sinSesion: true };
  const [esquema, ...resto] = encabezado.split(' ');
  // Como en Django, un esquema distinto de "Bearer" no es un intento de autenticación con JWT.
  if (esquema !== 'Bearer') return { sinSesion: true };
  return resto.length === 1 && resto[0] ? { token: resto[0] } : {};
};

// SimpleJWT guarda el id como texto ("7"); se acepta solo un entero positivo, sin signos ni decimales.
const ID_VALIDO = /^[1-9]\d*$/;

const esIdentidadValida = (datos) => datos.token_type === 'access'
  && ID_VALIDO.test(String(datos.usuario_id))
  && typeof datos.rol === 'string' && datos.rol.length > 0;

/**
 * Valida el access token que emite Django (SimpleJWT) con la clave compartida y deja en `req.usuario` su id y rol.
 * El refresh se firma con la misma clave: se exige `token_type: access` para que un refresh, que dura más, no
 * sirva como credencial. El algoritmo queda fijo en HS256 para que el token no pueda elegir cómo se verifica.
 */
export const autenticar = (req, res, next) => {
  const clave = process.env.JWT_SIGNING_KEY;
  if (!clave) return next(new Error('JWT_SIGNING_KEY no está configurada en backend-node.'));

  const { sinSesion, token } = leerToken(req.get('Authorization'));
  if (sinSesion) return rechazar(res, MENSAJE_SIN_SESION);
  if (!token) return rechazar(res, MENSAJE_TOKEN_INVALIDO);

  let datos;
  try {
    datos = jwt.verify(token, clave, { algorithms: ['HS256'] });
  } catch {
    return rechazar(res, MENSAJE_TOKEN_INVALIDO);
  }
  if (!esIdentidadValida(datos)) return rechazar(res, MENSAJE_TOKEN_INVALIDO);

  req.usuario = { id: Number(datos.usuario_id), rol: datos.rol };
  return next();
};
