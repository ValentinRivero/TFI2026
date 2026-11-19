export const ROLES = Object.freeze({
  JUGADOR: 'JUGADOR',
  DUENO_COMPLEJO: 'DUENO_COMPLEJO',
  OPERADOR_COMPLEJO: 'OPERADOR_COMPLEJO',
  SUPERADMIN: 'SUPERADMIN',
});

export const ROLES_DE_COMPLEJO = Object.freeze([ROLES.DUENO_COMPLEJO, ROLES.OPERADOR_COMPLEJO]);

const ROLES_EXISTENTES = new Set(Object.values(ROLES));

/**
 * Restringe una ruta a los roles indicados; va siempre después de `autenticar`. Solo controla el rol: que el
 * complejo pedido sea del usuario lo decide Django, que es quien conoce las asignaciones.
 */
export const permitirRoles = (...roles) => {
  const desconocidos = roles.filter((rol) => !ROLES_EXISTENTES.has(rol));
  // Un rol mal escrito falla al arrancar el servidor y no como un 403 silencioso en producción.
  if (roles.length === 0 || desconocidos.length > 0) {
    throw new Error(`permitirRoles recibió roles inválidos: [${desconocidos.join(', ')}]`);
  }
  const permitidos = new Set(roles);

  return (req, res, next) => {
    if (!req.usuario) return next(new Error('permitirRoles se usó sin el middleware autenticar.'));
    if (!permitidos.has(req.usuario.rol)) {
      return res.status(403).json({ error: true, mensaje: 'No tenés permiso para realizar esta acción.' });
    }
    return next();
  };
};
