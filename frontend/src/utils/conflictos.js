/**
 * Detalle de un `409` que pide confirmación (`requiere_confirmacion`): las reservas y los turnos fijos que el cambio
 * deja fuera de la grilla. Devuelve `null` si el error es de otra clase (un solapamiento, una regla incumplida), que
 * no se resuelve confirmando.
 */
export const leerConflictos = (error) => {
  if (error?.status !== 409 || error.extra?.requiere_confirmacion !== true) return null;
  const detalle = error.extra.conflictos ?? {};
  const reservas = Array.isArray(detalle.reservas) ? detalle.reservas : [];
  const turnosFijos = Array.isArray(detalle.turnos_fijos) ? detalle.turnos_fijos : [];
  return {
    mensaje: error.mensaje,
    cantidad: Number.isInteger(detalle.cantidad) ? detalle.cantidad : reservas.length + turnosFijos.length,
    reservas,
    turnosFijos,
    vistaPrevia: error.extra.vista_previa ?? null,
  };
};

/** Mismo cuerpo con la confirmación explícita que el backend exige para aplicar un cambio con consecuencias. */
export const conConfirmacion = (datos = {}) => ({ ...datos, confirmar: true });
