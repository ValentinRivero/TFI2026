const MENSAJES_POR_TIPO = {
  'entity.parse.failed': [400, 'El cuerpo de la solicitud no es un JSON válido.'],
  'entity.too.large': [413, 'El cuerpo de la solicitud supera el tamaño permitido.'],
};

export const rutaNoEncontrada = (req, res) => {
  res.status(404).json({ error: true, mensaje: 'No se encontró el recurso solicitado.' });
};

// Express reconoce el manejador de errores por sus cuatro parámetros: `next` es obligatorio aunque no se use.
export const manejarErrores = (error, req, res, next) => {
  const conocido = MENSAJES_POR_TIPO[error.type];
  if (conocido) {
    const [codigo, mensaje] = conocido;
    return res.status(codigo).json({ error: true, mensaje });
  }
  // El detalle de un error no previsto (rutas, hosts, credenciales) queda en el log y nunca en la respuesta.
  console.error(error);
  return res.status(500).json({ error: true, mensaje: 'Error interno del servidor.' });
};
