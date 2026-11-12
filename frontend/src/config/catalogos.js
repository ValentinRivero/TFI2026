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

/** Estados de una reserva cancelada (por el jugador o por el complejo); solo estas se reabren. */
export const ESTADOS_RESERVA_CANCELADOS = Object.freeze([4, 5]);

/** Estados a los que se puede reabrir una reserva cancelada: pendiente de seña, confirmada o señada. */
export const ESTADOS_REAPERTURA = Object.freeze([1, 2, 3]);

/**
 * Cambios de estado que admite la agenda por reserva (espejo de `TRANSICIONES_AGENDA` de Django). Ausente y
 * completada se corrigen entre sí; las canceladas no vuelven atrás por esta vía.
 */
export const TRANSICIONES_AGENDA = Object.freeze({
  1: Object.freeze([2, 3, 6, 7]),
  2: Object.freeze([3, 6, 7]),
  3: Object.freeze([6, 7]),
  6: Object.freeze([7]),
  7: Object.freeze([6]),
});

/** Ausente y completada solo se marcan una vez iniciado el turno. */
export const ESTADOS_QUE_EXIGEN_TURNO_INICIADO = Object.freeze([6, 7]);

/** Estados que el filtro de la agenda ofrece (todos salvo la baja lógica). */
export const ESTADOS_RESERVA_FILTRABLES = Object.freeze([1, 2, 3, 4, 5, 6, 7]);

/** Clave de cada conteo del dashboard con el código de estado de reserva que lo rotula (`canceladas_total` es la suma). */
export const CONTEO_REPORTE_POR_ESTADO = Object.freeze([
  Object.freeze({ clave: 'pendientes', estado: 1 }),
  Object.freeze({ clave: 'confirmadas', estado: 2 }),
  Object.freeze({ clave: 'senadas', estado: 3 }),
  Object.freeze({ clave: 'canceladas_jugador', estado: 4 }),
  Object.freeze({ clave: 'canceladas_complejo', estado: 5 }),
  Object.freeze({ clave: 'ausentes', estado: 6 }),
  Object.freeze({ clave: 'completadas', estado: 7 }),
]);

/** Fecha de la reserva que el dashboard compara con el rango (parámetro `criterio`). */
export const CRITERIO_REPORTE = Object.freeze({
  fecha_turno: entrada('Día en que se juega'),
  fecha_creacion: entrada('Día en que se registró'),
  fecha_modificacion: entrada('Día del último cambio'),
});

export const CRITERIO_REPORTE_POR_DEFECTO = 'fecha_turno';

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

/** Estados que admite el formulario de una cancha: la baja se hace con la acción de baja y no editando el estado. */
export const ESTADOS_CANCHA_EDITABLES = Object.freeze([1, 2]);

export const ESTADO_TURNO_FIJO = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Vigente', ok),
  2: entrada('Pausado', aviso),
});

export const TURNO_FIJO_VIGENTE = 1;
export const TURNO_FIJO_PAUSADO = 2;

/** Qué se hace con una fecha de turno fijo al llevarla a la agenda (campo `accion` de la API). */
export const ACCION_FECHA_TURNO_FIJO = Object.freeze({
  MANTENER: 'mantener',
  CANCELAR: 'cancelar',
});

export const ESTADO_CONTRATO = Object.freeze({
  0: entrada('Baja', neutro),
  1: entrada('Pendiente', aviso),
  2: entrada('Activo', ok),
  3: entrada('Suspendido', peligro),
});

/** Órdenes del listado de contratos (`ordering`), con la clave de texto que los rotula. */
export const ORDENES_CONTRATO = Object.freeze([
  Object.freeze({ valor: 'nombre', clave: 'contratos.ordenNombre' }),
  Object.freeze({ valor: '-nombre', clave: 'contratos.ordenNombreDesc' }),
  Object.freeze({ valor: 'estado_contrato', clave: 'contratos.ordenEstado' }),
  Object.freeze({ valor: '-fecha_creacion', clave: 'contratos.ordenReciente' }),
]);

/** Estados con los que se da de alta un contrato (los demás se alcanzan cambiando el estado). */
export const ESTADOS_CONTRATO_INICIALES = Object.freeze([1, 2]);

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

/** Vigencias del listado de excepciones (parámetro `vigencia` de la API); vacío trae vigentes y finalizadas. */
export const VIGENCIA_EXCEPCION = Object.freeze({ VIGENTES: 'vigentes', FINALIZADAS: 'finalizadas' });

/** Vistas de la agenda del complejo (parámetro `vista` de la ruta), con la clave de texto que las rotula. */
export const VISTA_AGENDA = Object.freeze({ RESERVAS: 'reservas', TURNOS_FIJOS: 'turnos-fijos' });

export const PESTANAS_AGENDA = Object.freeze([
  Object.freeze({ valor: VISTA_AGENDA.RESERVAS, clave: 'agenda.pestanaReservas' }),
  Object.freeze({ valor: VISTA_AGENDA.TURNOS_FIJOS, clave: 'agenda.pestanaTurnosFijos' }),
]);

export const ES_DIA_COMPLETO = 1;
export const ES_FRANJA_HORARIA = 0;

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

/** Vistas del catálogo: la lista de tarjetas (por defecto) y el mapa. `valor` es el que viaja en `?vista=`. */
export const VISTA_LISTA = 'lista';
export const VISTA_MAPA = 'mapa';
export const VISTAS_CATALOGO = Object.freeze([
  Object.freeze({ valor: VISTA_LISTA, clave: 'catalogo.vistaLista', icono: 'menu' }),
  Object.freeze({ valor: VISTA_MAPA, clave: 'catalogo.vistaMapa', icono: 'mapa' }),
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
  // Espejo de la matriz de permisos: el operador ve la configuración y las canchas, pero no las edita.
  configurarComplejo: [ROL.DUENO, ROL.SUPERADMIN],
  operadoresComplejo: [ROL.DUENO, ROL.SUPERADMIN],
  administrarCanchas: [ROL.DUENO, ROL.SUPERADMIN],
  excepciones: [ROL.OPERADOR, ROL.DUENO, ROL.SUPERADMIN],
  agenda: [ROL.OPERADOR, ROL.DUENO, ROL.SUPERADMIN],
  reportes: [ROL.DUENO, ROL.SUPERADMIN],
  sistema: [ROL.SUPERADMIN],
  perfil: Object.values(ROL),
  notificaciones: Object.values(ROL),
});

export const puedeVer = (seccion, rol) => Boolean(rol) && (ROLES_POR_SECCION[seccion] ?? []).includes(rol);

/** Opciones `{ valor, etiqueta }` de un catálogo para un `<select>`, con los códigos como texto y en el orden del catálogo. */
export const opcionesDe = (catalogo, codigos = Object.keys(catalogo)) => (
  codigos.map((codigo) => ({ valor: String(codigo), etiqueta: catalogo[codigo]?.etiqueta ?? String(codigo) }))
);

const DESCONOCIDO = Object.freeze({ etiqueta: 'Desconocido', badge: neutro });

/** Etiqueta y badge de un código; uno que el catálogo no conoce no rompe la pantalla. */
export const describir = (catalogo, codigo) => catalogo[codigo] ?? DESCONOCIDO;
