import mongoose from 'mongoose';

const MENSAJES_POR_TIPO = {
  'entity.parse.failed': [400, 'El cuerpo de la solicitud no es un JSON válido.'],
  'entity.too.large': [413, 'El cuerpo de la solicitud supera el tamaño permitido.'],
};

/** Error con código HTTP y mensaje pensado para el cliente: se responde tal cual. */
export class ErrorHttp extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.name = 'ErrorHttp';
    this.status = status;
  }
}

/** Falla de un servicio del que depende backend-node (Django, Open-Meteo): el cliente recibe un 502 genérico. */
export class ErrorServicioExterno extends ErrorHttp {
  constructor(servicio, causa) {
    super(502, 'Un servicio necesario no está disponible. Intentá nuevamente en unos minutos.');
    this.name = 'ErrorServicioExterno';
    this.servicio = servicio;
    this.cause = causa;
  }
}

export const rutaNoEncontrada = (req, res) => {
  res.status(404).json({ error: true, mensaje: 'No se encontró el recurso solicitado.' });
};

// Express reconoce el manejador de errores por sus cuatro parámetros: `next` es obligatorio aunque no se use.
export const manejarErrores = (error, req, res, next) => {
  if (error instanceof ErrorHttp) {
    return res.status(error.status).json({ error: true, mensaje: error.message });
  }
  if (error instanceof mongoose.Error.ValidationError) {
    // Mismo formato que validarCampos: un detalle por campo, sin repetir el valor recibido.
    const detalles = Object.values(error.errors).map((detalle) => ({
      campo: detalle.path,
      mensaje: detalle.kind === 'user defined' || detalle.kind === 'required' || detalle.kind === 'enum'
        ? detalle.message
        : 'Valor inválido.',
    }));
    return res.status(400).json({ error: true, mensaje: 'Datos inválidos.', detalles });
  }
  const conocido = MENSAJES_POR_TIPO[error.type];
  if (conocido) {
    const [codigo, mensaje] = conocido;
    return res.status(codigo).json({ error: true, mensaje });
  }
  // El detalle de un error no previsto (rutas, hosts, credenciales) queda en el log y nunca en la respuesta.
  console.error(error);
  return res.status(500).json({ error: true, mensaje: 'Error interno del servidor.' });
};
