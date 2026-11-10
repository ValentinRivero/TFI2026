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

// Django firma `rol: null` si el rol de la cuenta está desactivado: es una identidad válida sin permisos (403).
const esRolValido = (rol) => rol === null || (typeof rol === 'string' && rol.length > 0);

const esIdentidadValida = (datos) => datos.token_type === 'access'
  && ID_VALIDO.test(String(datos.usuario_id))
  && esRolValido(datos.rol);

const identificar = (token, clave) => {
  try {
    const datos = jwt.verify(token, clave, { algorithms: ['HS256'] });
    return esIdentidadValida(datos) ? { id: Number(datos.usuario_id), rol: datos.rol } : null;
  } catch {
    return null;
  }
};

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

  const usuario = identificar(token, clave);
  if (!usuario) return rechazar(res, MENSAJE_TOKEN_INVALIDO);

  req.usuario = usuario;
  return next();
};

/**
 * Para rutas públicas: con un token válido deja el usuario en `req.usuario`; sin token, o con uno inválido o
 * vencido, sigue como anónimo, igual que las rutas públicas de Django, para que un access vencido no corte la visita.
 */
export const autenticarOpcional = (req, res, next) => {
  const { token } = leerToken(req.get('Authorization'));
  if (!token) return next();
  const clave = process.env.JWT_SIGNING_KEY;
  if (!clave) return next(new Error('JWT_SIGNING_KEY no está configurada en backend-node.'));
  const usuario = identificar(token, clave);
  if (usuario) req.usuario = usuario;
  return next();
};
