const origenesPermitidos = () => (process.env.CORS_ALLOWED_ORIGINS ?? '')
  .split(',')
  .map((origen) => origen.trim())
  .filter(Boolean);

export const crearOpcionesCors = () => {
  const permitidos = new Set(origenesPermitidos());
  return {
    // Sin encabezado Origin la petición no viene de un navegador (servicios, healthchecks) y CORS no aplica.
    origin: (origen, responder) => responder(null, !origen || permitidos.has(origen)),
    methods: ['GET', 'POST', 'PATCH'],
    allowedHeaders: ['Authorization', 'Content-Type'],
    // La sesión viaja en el encabezado Authorization: no hay cookies que habilitar entre orígenes.
    credentials: false,
    maxAge: 600,
  };
};
