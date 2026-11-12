/**
 * Códigos numéricos de los backends (`IntegerChoices` de Django y enumeraciones de Node) con su etiqueta y la
 * clase de badge que los pinta. Las clases (`badge-ok`, `badge-aviso`, `badge-peligro`, `badge-neutro` y
 * `badge-info`) se definen en `styles/tema.css`. Espejo de los backends: cualquier código nuevo se suma en ambos.
 */
const ok = 'badge-ok';
const aviso = 'badge-aviso';
const peligro = 'badge-peligro';
const neutro = 'badge-neutro';
const info = 'badge-info';

const entrada = (etiqueta, badge = neutro) => Object.freeze({ etiqueta, badge });

export const ESTADO_RESERVA = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Pendiente de seña', aviso),
  2: entrada('Confirmada', info),
  3: entrada('Señada o pagada', ok),
  4: entrada('Cancelada por el jugador', peligro),
  5: entrada('Cancelada por el complejo', peligro),
  6: entrada('Ausente', neutro),
  7: entrada('Completada', ok),
});

export const RESERVA_SENADA = 3;

/** Estados desde los que el jugador puede cancelar: pendiente de seña, confirmada y señada o pagada. */
export const ESTADOS_RESERVA_CANCELABLES = Object.freeze([1, 2, 3]);

/** Vistas de "Mis reservas" (parámetro `vigencia` de la API), con la clave de texto que las rotula. */
export const VIGENCIA_RESERVA = Object.freeze({
  PROXIMAS: 'proximas',
  PASADAS: 'pasadas',
});

export const PESTANAS_RESERVA = Object.freeze([
  Object.freeze({ valor: VIGENCIA_RESERVA.PROXIMAS, clave: 'misReservas.proximas' }),
  Object.freeze({ valor: VIGENCIA_RESERVA.PASADAS, clave: 'misReservas.historial' }),
]);

export const ESTADO_CANCHA = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Activa', ok),
  2: entrada('En mantenimiento', aviso),
});

export const ESTADO_TURNO_FIJO = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Vigente', ok),
  2: entrada('Pausado', aviso),
});

export const ESTADO_CONTRATO = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Pendiente', aviso),
  2: entrada('Activo', ok),
  3: entrada('Suspendido', peligro),
});

export const ESTADO_USUARIO = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Activo', ok),
  2: entrada('Suspendido', peligro),
});

export const ALCANCE_EXCEPCION = Object.freeze({
  0: entrada('Franja horaria', info),
  1: entrada('Día completo', aviso),
});

export const TIPO_SUPERFICIE = Object.freeze({
  1: entrada('Césped sintético'),
  2: entrada('Césped natural'),
  3: entrada('Cemento'),
  4: entrada('Parquet'),
  5: entrada('Polvo de ladrillo'),
  6: entrada('Arena'),
});

export const COBERTURA = Object.freeze({
  1: entrada('Descubierta'),
  2: entrada('Techada'),
  3: entrada('Semicubierta'),
});

export const ILUMINACION = Object.freeze({
  1: entrada('Sin iluminación'),
  2: entrada('Halógena'),
  3: entrada('LED'),
});

export const DURACION_TURNO = Object.freeze({
  60: entrada('60 minutos'),
  90: entrada('90 minutos'),
  120: entrada('120 minutos'),
});

export const DIA_SEMANA = Object.freeze({
  0: entrada('Lunes'),
  1: entrada('Martes'),
  2: entrada('Miércoles'),
  3: entrada('Jueves'),
  4: entrada('Viernes'),
  5: entrada('Sábado'),
  6: entrada('Domingo'),
});

export const TIPO_MOTIVO_EXCEPCION = Object.freeze({
  1: entrada('Mantenimiento', aviso),
  2: entrada('Condiciones climáticas', info),
  3: entrada('Feriado', info),
  4: entrada('Evento privado', info),
  5: entrada('Corte de servicio', peligro),
  6: entrada('Otro', neutro),
});

export const TIPO_OCUPACION = Object.freeze({
  1: entrada('Reserva web', info),
  2: entrada('Reserva manual', neutro),
  3: entrada('Turno fijo', ok),
});

export const TIPO_EVENTO_AUDITORIA = Object.freeze({
  1: entrada('Inicio de sesión', ok),
  2: entrada('Inicio de sesión fallido', peligro),
  3: entrada('Cierre de sesión', neutro),
  4: entrada('Acceso denegado', peligro),
  5: entrada('Límite de peticiones superado', aviso),
  6: entrada('Registro de usuario', info),
  7: entrada('Baja de usuario', neutro),
  8: entrada('Cambio de contrato', aviso),
  9: entrada('Alta de excepción', info),
  10: entrada('Baja de excepción', neutro),
  11: entrada('Reserva creada', ok),
  12: entrada('Reserva cancelada', peligro),
  13: entrada('Cambio de estado de reserva', info),
  14: entrada('Cambio de configuración', info),
  15: entrada('Aceptación de la política', ok),
  16: entrada('Cambio de usuario', aviso),
});

export const CATEGORIA_NOTIFICACION = Object.freeze({
  1: entrada('Reservas', info),
  2: entrada('Cuentas', neutro),
  3: entrada('Operatoria', aviso),
  4: entrada('Sistema', neutro),
});

export const PRIORIDAD_NOTIFICACION = Object.freeze({
  1: entrada('Normal', neutro),
  2: entrada('Urgente', peligro),
});

export const ESTADO_NOTIFICACION = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('No leída', info),
  2: entrada('Leída', neutro),
});

export const TIPO_EVENTO_ACTIVIDAD = Object.freeze({
  1: entrada('Complejo visto', neutro),
  2: entrada('Grilla consultada', neutro),
  3: entrada('Reserva realizada', ok),
});

/** Tipos de evento que el cliente informa a `backend-node`; el 3 lo emite Django. */
export const EVENTO_ACTIVIDAD = Object.freeze({ COMPLEJO_VISTO: 1, GRILLA_CONSULTADA: 2, RESERVA_REALIZADA: 3 });

/** Órdenes que admite el catálogo (`ordering`), con la clave de texto que los rotula. */
export const ORDENES_CATALOGO = Object.freeze([
  Object.freeze({ valor: 'nombre', clave: 'filtros.ordenNombre' }),
  Object.freeze({ valor: '-nombre', clave: 'filtros.ordenNombreDesc' }),
  Object.freeze({ valor: 'precio_desde', clave: 'filtros.ordenPrecio' }),
  Object.freeze({ valor: '-precio_desde', clave: 'filtros.ordenPrecioDesc' }),
]);

export const BLOQUE_LIBRE = 'LIBRE';

/** Estados de un bloque de la grilla, con el nombre del casillero que los dibuja en `tema.css`. */
export const ESTADO_BLOQUE = Object.freeze({
  LIBRE: Object.freeze({ etiqueta: 'Libre', casillero: 'libre' }),
  OCUPADO: Object.freeze({ etiqueta: 'Ocupado', casillero: 'ocupado' }),
  CERRADO_EXCEPCION: Object.freeze({ etiqueta: 'Cerrado', casillero: 'excepcion' }),
  NO_DISPONIBLE: Object.freeze({ etiqueta: 'No disponible', casillero: 'no-disponible' }),
});

export const ROL = Object.freeze({
  SUPERADMIN: 'SUPERADMIN',
  DUENO: 'DUENO_COMPLEJO',
  OPERADOR: 'OPERADOR_COMPLEJO',
  JUGADOR: 'JUGADOR',
});

export const ETIQUETA_ROL = Object.freeze({
  SUPERADMIN: 'Superadministrador',
  DUENO_COMPLEJO: 'Dueño de complejo',
  OPERADOR_COMPLEJO: 'Operador de complejo',
  JUGADOR: 'Jugador',
});

/** Pantalla a la que lleva el inicio de sesión cuando no venía redirigido desde otra ruta. */
export const RUTA_INICIAL_POR_ROL = Object.freeze({
  SUPERADMIN: '/sistema',
  DUENO_COMPLEJO: '/panel',
  OPERADOR_COMPLEJO: '/panel',
  JUGADOR: '/',
});

/** Secciones de la navegación por rol. El control real lo hacen los backends: acá solo se decide qué se muestra. */
export const ROLES_POR_SECCION = Object.freeze({
  misReservas: [ROL.JUGADOR, ROL.SUPERADMIN],
  reservar: [ROL.JUGADOR, ROL.SUPERADMIN],
  panel: [ROL.OPERADOR, ROL.DUENO, ROL.SUPERADMIN],
  reportes: [ROL.DUENO, ROL.SUPERADMIN],
  sistema: [ROL.SUPERADMIN],
  perfil: Object.values(ROL),
  notificaciones: Object.values(ROL),
});

export const puedeVer = (seccion, rol) => Boolean(rol) && (ROLES_POR_SECCION[seccion] ?? []).includes(rol);

const DESCONOCIDO = Object.freeze({ etiqueta: 'Desconocido', badge: neutro });

/** Etiqueta y badge de un código; uno que el catálogo no conoce no rompe la pantalla. */
export const describir = (catalogo, codigo) => catalogo[codigo] ?? DESCONOCIDO;
