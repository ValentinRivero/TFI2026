# API de TaLibre

Referencia de los endpoints vigentes del backend principal. Todas las rutas cuelgan de `/api/`, reciben y devuelven JSON y se sirven solo por HTTPS en producción.

## Convenciones

**Autenticación.** Las rutas privadas esperan `Authorization: Bearer <access>`. El access dura poco y se renueva con `POST /api/token/refresh/`: el refresh viaja en una cookie `HttpOnly` que gestiona el navegador y que JavaScript no puede leer. Las rutas públicas ignoran el encabezado `Authorization`.

**Acceso.** Cada ruta indica el rol mínimo. El superadmin puede operar sobre cualquier complejo; dueño y operador, solo sobre el suyo. Un recurso de otro complejo responde `404`, igual que uno inexistente.

**Errores.** Siempre con la misma forma; `detail` es un texto o un objeto con un mensaje por campo:

```json
{ "error": true, "detail": "No se encontró el recurso solicitado." }
```

| Código | Significado |
|---|---|
| 400 | Datos inválidos o regla de negocio incumplida |
| 401 | Falta iniciar sesión, o el token es inválido o venció |
| 403 | Sesión válida sin permiso para la acción |
| 404 | No existe o no es accesible para el usuario |
| 405 | Método no admitido en la ruta |
| 409 | El turno choca con una reserva, un turno fijo o una excepción horaria |
| 429 | Demasiadas solicitudes; reintentar más tarde |

**Listados.** Paginados de a 20: `{ "count", "next", "previous", "results" }`, con `?page=`. Los filtros aceptan solo los parámetros documentados; un valor inválido responde `400` y un parámetro desconocido se ignora. `?search=` no distingue mayúsculas ni tildes, y varios términos separados por espacios se exigen todos.

**Bajas.** Ningún `DELETE` borra datos: aplica una baja lógica.

## Sesión y perfil

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/health/` | Público | Estado del servicio |
| `POST /api/registro/` | Público | Alta de jugador: `nombre_completo`, `email`, `password`, `telefono` (opcional) y `acepta_politica_privacidad: true` |
| `POST /api/token/` | Público | Inicio de sesión con `email` y `password`; devuelve `{ access }` y la cookie de sesión |
| `POST /api/token/refresh/` | Cookie de sesión | Nuevo `{ access }` |
| `POST /api/token/logout/` | Cookie de sesión | Cierra la sesión (`204`) |
| `GET /api/perfil/` | Autenticado | Datos propios; `debe_aceptar_politica` indica si hay una versión nueva de la política |
| `PATCH /api/perfil/` | Autenticado | `nombre_completo`, `telefono` o `acepta_politica_privacidad: true` |
| `GET /api/perfil/baja/` | Autenticado | Vista previa de la baja: qué reservas y turnos fijos se cancelan y cuáles se conservan |
| `DELETE /api/perfil/` | Autenticado | Baja de la cuenta propia con anonimización de datos personales (`204`) |

El registro y el inicio de sesión tienen un límite de intentos por origen y responden `429` al superarlo.

### Baja de la cuenta propia

```json
{
  "reservas_a_cancelar": 2, "reservas_senadas_conservadas": 1, "turnos_fijos_a_dar_de_baja": 1,
  "avisos": ["1 reserva señada o pagada no se cancela: el complejo decide si la mantiene, la reprograma o devuelve la seña. ..."],
  "impedimento": null
}
```

- `GET /api/perfil/baja/` no modifica nada; conviene mostrarlo antes de confirmar el `DELETE`. `impedimento` trae el motivo por el que hoy se rechazaría la baja (por ejemplo, ser el único superadministrador o tener contratos vigentes), o `null`.
- Al confirmar la baja, las reservas por jugar pendientes de seña o confirmadas se cancelan (`estado = 4`) y sus horarios quedan libres en la grilla.
- Las señadas o pagadas no se cancelan, porque las resuelve el complejo. En esas reservas se conservan el nombre y el teléfono del titular solo para resolver la seña: se borran al resolverse o, como máximo, 30 días después del turno.
- Los turnos fijos del titular se dan de baja. El complejo recibe un aviso.

## Catálogo público

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/deportes/` | Público | Deportes disponibles (lista completa, sin paginar) |
| `GET /api/servicios/` | Público | Servicios disponibles (lista completa, sin paginar) |
| `GET /api/complejos/` | Público | Complejos habilitados, con coordenadas, servicios, deportes y `precio_desde` |
| `GET /api/complejos/<id>/` | Público | Detalle con sus canchas activas; `404` si el complejo no está habilitado |
| `GET /api/complejos/<id>/grilla/?fecha=AAAA-MM-DD` | Público | Turnos del día por cancha, con precio y estado (respuesta completa, sin paginar) |

Filtros de `GET /api/complejos/`: `deporte` (id), `cobertura` (`1` descubierta, `2` techada, `3` semicubierta), `servicio` (id, repetible: se exigen todos), `search` (nombre o dirección) y `ordering` (`nombre`, `precio_desde`, con `-` para invertir). `deporte` y `cobertura` se cumplen sobre una misma cancha.

### Grilla del día

`fecha` es obligatoria, en formato `AAAA-MM-DD`, y no puede ser anterior a hoy (`400`). Un complejo no habilitado responde `404`.

```json
{
  "complejo": { "id": 1, "nombre": "Complejo El Yacaré" },
  "fecha": "2026-11-18",
  "dia_semana": 2,
  "canchas": [
    {
      "id": 3, "nombre": "Cancha 1", "deporte": { "id": 1, "nombre": "Fútbol 5" }, "duracion_turno_min": 60,
      "bloques": [
        { "hora_inicio": "14:00:00", "hora_fin": "15:00:00", "precio": "38000.00", "estado": "LIBRE", "motivo": null },
        { "hora_inicio": "15:00:00", "hora_fin": "16:00:00", "precio": "38000.00", "estado": "OCUPADO", "motivo": null },
        { "hora_inicio": "16:00:00", "hora_fin": "17:00:00", "precio": "38000.00", "estado": "CERRADO_EXCEPCION", "motivo": "Mantenimiento" }
      ]
    }
  ]
}
```

- Cada rango horario del día genera sus turnos por separado según `duracion_turno_min`; un resto menor a un turno completo no se ofrece. Una cancha sin horario ese día figura con `bloques` vacío.
- `estado`: `LIBRE`, `OCUPADO` (reserva activa o turno fijo), `CERRADO_EXCEPCION`, con el motivo del cierre en `motivo`, o `NO_DISPONIBLE` (un turno de hoy que ya empezó, o de una fecha posterior a los 2 meses de anticipación que admiten las reservas). Si un turno ya ocupado coincide con un cierre, se informa `OCUPADO`.
- Todo turno `LIBRE` se puede reservar con `POST /api/reservas/`.
- La respuesta no incluye datos de quien reservó.

### Disponibilidad en tiempo real (WebSocket)

`wss://<dominio>/ws/complejos/<id>/disponibilidad/` mantiene al día la grilla abierta de un complejo. Es público y de solo lectura: `?token=<access>` es opcional y un token vencido o inválido no impide conectarse.

```json
{ "event": "grilla_actualizada", "cancha_id": 3, "fecha_desde": "2026-11-18", "fecha_hasta": "2026-11-18", "hora_inicio": "20:00:00", "hora_fin": "21:00:00" }
```

- El evento avisa que cambió la disponibilidad en ese rango. Si la fecha que se está viendo cae entre `fecha_desde` y `fecha_hasta`, se vuelve a pedir la grilla por REST.
- `cancha_id` nulo: afecta a todas las canchas del complejo. Horas nulas: el día completo. `fecha_hasta` nulo: sin fecha de fin (turno fijo por tiempo indefinido).
- No lleva datos de quien reservó.
- Los mensajes que envía el cliente se ignoran.
- Un complejo no habilitado o inexistente rechaza la conexión, igual que una página de otro origen.
- Si la conexión se corta, al reconectar se vuelve a pedir la grilla por REST: los eventos perdidos no se reenvían.
- Para no recargar de más: ante un evento, pedir la grilla solo si la fecha que se está viendo cae en el rango y `cancha_id` es nulo o es una de las canchas mostradas; y agrupar los eventos que lleguen casi juntos (alrededor de 1 segundo) en una sola recarga.
- La grilla tiene su propio límite de solicitudes por origen, más amplio que el del resto de las rutas públicas, y responde `429` al superarlo.
- Los cambios de canchas y horarios también se anuncian, con `cancha_id`, `fecha_desde` igual a hoy, `fecha_hasta` nulo y horas nulas. Si el complejo deja de estar habilitado, el servidor cierra las conexiones abiertas.

## Reservas del jugador

| Método y ruta | Acceso | Uso |
|---|---|---|
| `POST /api/reservas/` | Jugador | `cancha`, `fecha_turno` (`AAAA-MM-DD`) y `hora_inicio` (`HH:MM`) de un turno libre de la grilla |
| `GET /api/reservas/mias/` | Jugador | Reservas propias; filtros `estado`, `vigencia` (`proximas` o `pasadas`), `fecha_desde` y `fecha_hasta`; `ordering` por `fecha_turno`, `hora_inicio` o `fecha_creacion` |
| `POST /api/reservas/<id>/cancelar/` | Jugador | Cancela una reserva propia (`estado = 4`) |

```json
{
  "id": 41, "complejo": { "id": 1, "nombre": "Complejo El Yacaré" }, "cancha": { "id": 3, "nombre": "Cancha 1" },
  "deporte": "Fútbol 5", "fecha_turno": "2026-11-24", "hora_inicio": "20:00:00", "hora_fin": "21:00:00",
  "precio_acordado": "38000.00", "tipo_ocupacion": 1, "tipo_ocupacion_nombre": "Reserva web del jugador",
  "estado": 1, "estado_nombre": "Pendiente Seña", "cancelable_hasta": "2026-11-24T16:00:00-03:00",
  "fecha_creacion": "2026-11-16T10:00:00-03:00"
}
```

- Rutas de jugadores (y del superadmin): dueños y operadores registran reservas desde la agenda.
- `hora_inicio` debe ser el inicio de un turno de la grilla de esa fecha. `hora_fin` y `precio_acordado` los calcula el servidor según la cancha y su horario; si se envían, se ignoran. La reserva nace pendiente de seña (`estado = 1`).
- Se reserva con hasta 2 meses calendario de anticipación (por ejemplo, el 16/11 hasta el 16/01 inclusive).
- `400`: turno pasado o ya iniciado, fecha más allá de la anticipación máxima, horario que no es un turno de la cancha, cancha no disponible o complejo no habilitado. `409`: el turno ya está reservado, lo ocupa un turno fijo o lo cierra una excepción; el mensaje indica cuál.
- Las altas tienen un límite de solicitudes por cuenta y responden `429` al superarlo; consultar y cancelar no cuentan.
- `vigencia=proximas` incluye las reservas cuyo turno todavía no terminó (la de hoy en curso también); `pasadas`, las ya terminadas.
- Solo se cancelan reservas en `1`, `2` o `3`, y si faltan más horas que el margen del complejo (`horas_limite_cancelacion`) para el inicio del turno; `cancelable_hasta` informa el límite. Fuera de margen responde `400`. Una reserva de otra cuenta responde `404`.
- `estado`: `1` pendiente de seña, `2` confirmada, `3` señada o pagada, `4` cancelada por el jugador, `5` cancelada por el complejo, `6` ausente, `7` completada.

## Administración del complejo

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/complejos/administrados/` | Operador | Complejos que el usuario puede administrar |
| `PATCH /api/complejos/<id>/` | Dueño | `nombre`, `direccion`, `latitud`, `longitud`, `telefono_contacto`, `horas_limite_cancelacion`, `info_sena` |
| `PUT /api/complejos/<id>/servicios/` | Dueño | `{ "servicios": [ids] }`: deja activos exactamente esos servicios |
| `GET /api/complejos/<id>/operadores/` | Dueño | Operadores del complejo |
| `POST /api/complejos/<id>/operadores/` | Dueño | `{ "email" }` de una cuenta de operador sin complejo asignado |
| `DELETE /api/complejos/<id>/operadores/<usuario_id>/` | Dueño | Desvincula al operador (la cuenta sigue activa) |

### Canchas

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/canchas/` | Operador | Canchas vigentes; filtros `complejo`, `deporte`, `estado` (`1` activa, `2` en mantenimiento); `ordering` por `nombre` o `precio_base` |
| `GET /api/canchas/<id>/` | Operador | Detalle |
| `POST /api/canchas/` | Dueño | `complejo`, `deporte`, `nombre`, `tipo_superficie`, `cobertura`, `iluminacion`, `duracion_turno_min` (`60`, `90` o `120`), `precio_base` |
| `PATCH /api/canchas/<id>/` | Dueño | Cualquier campo salvo `complejo`; `estado` admite `1` o `2`. Con `confirmar` (ver abajo) |
| `DELETE /api/canchas/<id>/` | Dueño | Baja; `400` si tiene reservas o turnos fijos vigentes, sin confirmación posible |

### Horarios de apertura

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/horarios/` | Operador | Rangos vigentes; filtros `cancha` y `dia_semana` (`0` lunes a `6` domingo) |
| `GET /api/horarios/<id>/` | Operador | Detalle |
| `POST /api/horarios/` | Dueño | `cancha`, `dia_semana`, `hora_apertura`, `hora_cierre` (`HH:MM`) y `precio_diferenciado` opcional |
| `PATCH /api/horarios/<id>/` | Dueño | Cualquier campo salvo `cancha`. Con `confirmar` (ver abajo) |
| `DELETE /api/horarios/<id>/` | Dueño | Baja del rango; `?confirmar=true` o `{ "confirmar": true }` (ver abajo) |

Un día admite varios rangos por cancha mientras no se superpongan; `hora_cierre` debe ser posterior a `hora_apertura`. Sin `precio_diferenciado` rige el `precio_base` de la cancha.

### Cambios que afectan reservas futuras

Los cambios de operatoria se revisan antes de aplicarse:
- editar el día o el horario de un rango;
- darlo de baja;
- cambiar `duracion_turno_min`;
- pasar una cancha a mantenimiento.

Si el cambio deja reservas por jugar (pendientes, confirmadas o señadas) o turnos fijos fuera de los turnos de la grilla, responde `409` sin aplicar nada:

```json
{
  "error": true,
  "detail": "El cambio deja fuera de la grilla 1 reserva(s) futura(s) y 0 turno(s) fijo(s). ...",
  "requiere_confirmacion": true,
  "conflictos": {
    "cantidad": 1,
    "reservas": [{ "id": 41, "fecha_turno": "2026-11-24", "hora_inicio": "20:00:00", "estado": 3,
                   "motivo": "El turno ya no coincide con los horarios ni con la duración vigentes de la cancha." }],
    "turnos_fijos": []
  }
}
```

- Repetir la operación con `confirmar: true` aplica el cambio. Las reservas y los turnos fijos afectados no se cancelan: quedan marcados en la agenda para reprogramarlos o cancelarlos.
- Pide confirmación por lo que el cambio afecta por primera vez o con un motivo distinto del que ya tenía (por ejemplo, una reserva ya marcada fuera de turno cuando la cancha pasa a mantenimiento). Lo ya marcado y sin novedades no vuelve a frenar. Agregar un rango o cambiar un precio nunca pide confirmación.
- La respuesta no incluye datos de clientes.

### Excepciones horarias

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/excepciones/` | Operador | Excepciones activas; filtros `complejo`, `cancha` (incluye las de todo su complejo), `vigencia` (`vigentes` o `finalizadas`), `fecha` (`AAAA-MM-DD`, las que la cubren) y `tipo_motivo`; `ordering` por `fecha_inicio` o `fecha_creacion` |
| `GET /api/excepciones/<id>/` | Operador | Detalle |
| `POST /api/excepciones/` | Operador | `complejo`, `cancha` (opcional), `fecha_inicio`, `fecha_fin`, `es_dia_completo`, `hora_inicio`, `hora_fin`, `tipo_motivo` y `descripcion` (opcional) |
| `DELETE /api/excepciones/<id>/` | Operador | Baja de la excepción (`204`) |

- Sin `cancha`, la excepción cierra todo el complejo; con `cancha`, debe ser una cancha activa de ese complejo.
- `es_dia_completo`: `1` cierra el día entero y no lleva horas; `0` es una franja y exige `hora_inicio` y `hora_fin` (`HH:MM`), con el fin posterior al inicio.
- `fecha_fin` debe ser igual o posterior a `fecha_inicio`, que no puede ser anterior a hoy. El rango tiene una extensión máxima.
- `tipo_motivo`: `1` mantenimiento, `2` condiciones climáticas, `3` feriado, `4` evento privado, `5` corte de servicio, `6` otro.
- No se editan: para corregir una excepción se da de baja y se registra otra.

### Agenda

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/agenda/` | Operador | Reservas de los complejos administrados, con el contacto del cliente; filtros `complejo`, `cancha`, `fecha`, `fecha_desde`, `fecha_hasta`, `estado` y `tipo_ocupacion` (`1` web, `2` manual, `3` turno fijo); `ordering` por `fecha_turno`, `hora_inicio` o `fecha_creacion` |
| `GET /api/agenda/<id>/` | Operador | Detalle |
| `POST /api/agenda/` | Operador | Reserva telefónica o presencial: `cancha`, `fecha_turno`, `hora_inicio`, `nombre_cliente_manual` y, opcionales, `telefono_cliente_manual` y `observaciones` |
| `PATCH /api/agenda/<id>/` | Operador | `estado` y `observaciones` |
| `POST /api/agenda/<id>/cancelar/` | Operador | Cancela la reserva (`estado = 5`) sin restricción horaria |
| `POST /api/agenda/<id>/reabrir/` | Operador | `{ "estado", "confirmar" }`: reabre una reserva cancelada por error (`estado`: `1`, `2` o `3`) |

- Cada reserva trae `cliente`: `{ "nombre", "telefono", "email" }`. Es la cuenta del jugador si reservó en la web; si se cargó a mano, `email` es `null`. Si el titular dio de baja su cuenta, figura el contacto conservado para resolver una seña, o "Titular dado de baja".
- `conflicto_operatoria` trae el motivo por el que una reserva por jugar quedó fuera de la grilla tras un cambio de horarios, de duración o el paso a mantenimiento, o `null`. `?con_conflicto=true` lista solo esas reservas; la marca desaparece al resolverlas.
- El alta manual sigue las mismas reglas que la reserva web (turno de la grilla, futuro, dentro de la anticipación máxima y libre) y responde `409` ante un choque. Una cancha de otro complejo responde `403`.
- En `PATCH`, `cancha`, `fecha_turno`, `hora_inicio`, `hora_fin` y `precio_acordado` no se editan: enviados con otro valor responden `400` con el motivo; con el mismo valor se aceptan. Para cambiar el turno se cancela la reserva y se registra otra.
- `estado` en `PATCH` admite `2` confirmada, `3` señada, `6` ausente y `7` completada. Desde pendiente se pasa a cualquiera de ellas, desde confirmada a señada, ausente o completada, y desde señada a ausente o completada; ausente y completada se corrigen entre sí. Ausente y completada exigen que el turno haya empezado. Una reserva cancelada no cambia de estado por `PATCH`: se reabre con `reabrir/`.
- `reabrir/` solo acepta reservas canceladas (`4` o `5`) de turnos que todavía no empezaron, y no las de una cuenta dada de baja.
  - **Validación:** vuelve a validar el turno como un alta. Si lo tomó otra reserva o un turno fijo, lo cerró una excepción, la cancha cambió de horario o dejó de estar disponible, responde `409` sin opción de confirmar.
  - **Confirmación:** si el turno está libre y no se envía `confirmar: true`, responde `409` con `requiere_confirmacion: true` y una `vista_previa` (`id`, `fecha_turno`, `hora_inicio`, `hora_fin`, `estado_actual`, `estado_nuevo`). Con `confirmar: true` la reserva vuelve a ocupar su turno.
- Las reservas no se borran: se cancelan.

### Turnos fijos

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/turnos-fijos/` | Operador | Turnos fijos vigentes y pausados, con el contacto del cliente; filtros `cancha`, `complejo`, `dia_semana`, `estado` (`1` vigente, `2` pausado) y `fecha` (los que caen ese día) |
| `GET /api/turnos-fijos/<id>/` | Operador | Detalle |
| `POST /api/turnos-fijos/` | Operador | `cancha`, `dia_semana`, `hora_inicio`, `fecha_inicio_vigencia`, `fecha_fin_vigencia` (opcional, sin fin si es nula), `nombre_cliente_manual` y `telefono_cliente_manual` (opcional) |
| `PATCH /api/turnos-fijos/<id>/` | Operador | `estado` (`1` o `2`), `fecha_fin_vigencia`, `hora_inicio` (con `confirmar`), `nombre_cliente_manual` y `telefono_cliente_manual` |
| `DELETE /api/turnos-fijos/<id>/` | Operador | Baja del turno fijo (`204`) |
| `POST /api/turnos-fijos/<id>/fechas/` | Operador | `{ "fecha_turno", "accion" }`: lleva esa fecha a la agenda (`tipo_ocupacion = 3`); `accion` `mantener` (por defecto, confirmada) o `cancelar` (cancelada por el complejo) |

- `hora_fin` la calcula el servidor según la duración del turno de la cancha, y `hora_inicio` debe ser el inicio de un turno de la grilla ese día de la semana. La vigencia empieza hoy o después e incluye al menos una fecha de ese día.
- `409` si en alguna fecha futura de la vigencia choca con otro turno fijo vigente o una reserva activa; el mensaje indica la fecha o el horario. Una excepción no lo impide: esas fechas quedan en espera (ver abajo).
- La cancha, el día y el inicio de la vigencia no se editan: enviados con otro valor responden `400` con el motivo; con el mismo valor se aceptan. Pausar (`estado = 2`) libera el horario; reanudar y extender `fecha_fin_vigencia` vuelven a validar choques (`409`).
- **Cambio de horario** (`hora_inicio`):
  - **Validación:** el nuevo horario debe ser un turno de la grilla ese día (si no, `400`); `hora_fin` se recalcula. Se valida contra otros turnos fijos y reservas en toda la vigencia (`409` sin opción de confirmar).
  - **Confirmación:** sin `confirmar: true` responde `409` con `requiere_confirmacion` y una `vista_previa` (`horario_actual`, `horario_nuevo`, `rige_desde` y `fechas_registradas`).
  - **Fechas ya registradas:** conservan el horario anterior y se resuelven desde la agenda.
- `?fecha=` trae los vigentes y los pausados que caen ese día; con `estado=1`, solo los vigentes. `?en_espera=true` trae los que tienen fechas en espera.
- **Fechas en espera** (`fechas_en_espera: [{ "fecha", "motivo" }]`):
  - **Qué son:** las fechas de un turno fijo vigente que cubre una excepción activa (por ejemplo, un feriado), aunque se haya cargado después del turno fijo, y que el complejo todavía no decidió.
  - **Mientras esperan:** siguen ocupadas en la grilla.
  - **Cómo se deciden:** con `fechas/` y `accion`. `mantener` registra la fecha confirmada; `cancelar` la registra cancelada y el cierre de la excepción vuelve a regir. En los dos casos deja de estar en espera.
  - **Aviso:** crear una excepción que deja fechas en espera genera un aviso urgente para el complejo.
- Un turno fijo vigente ocupa su horario en cada fecha de su vigencia. Para operar una fecha puntual (señarla, completarla o cancelarla) se registra con `fechas/` y se gestiona desde la agenda; cancelarla libera solo ese día. La fecha debe ser de ese día de la semana y estar dentro de la vigencia; si ya se registró, responde `409`.
- La baja no cancela las fechas ya registradas en la agenda.
- `conflicto_operatoria`: igual que en la agenda, marca los turnos fijos vigentes o pausados que un cambio de operatoria dejó fuera de la grilla.

### Reportes

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/reportes/dashboard/` | Dueño | Dashboard de un complejo en un rango de fechas: `complejo`, `fecha_desde` y `fecha_hasta` (`AAAA-MM-DD`, obligatorios), `criterio` y, opcionales, `cancha_id` y `deporte_id` |

- `criterio` indica qué fecha de la reserva se compara con el rango: `fecha_turno` (por defecto, el día que se juega), `fecha_creacion` (el día que se registró) o `fecha_modificacion` (el último cambio, por ejemplo una cancelación).
- El rango incluye ambos extremos, `fecha_hasta` no puede ser anterior a `fecha_desde` y abarca como máximo 366 días; si no, responde `400`.
- `cancha_id` debe ser una cancha del complejo, incluidas las que están en mantenimiento o dadas de baja, que conservan su historial; si no, responde `400`. `deporte_id` debe ser un deporte existente. Ambos filtros se combinan.
- Se consulta también con el contrato pendiente o suspendido. Un complejo dado de baja o ajeno responde `404`; el operador no accede a los reportes (`403`).
- Con `fecha_creacion` y `fecha_modificacion`, los días se cuentan en hora de Argentina: una reserva registrada el 30/11 a las 23:30 entra en noviembre.
- La respuesta incluye `filtros` con los valores aplicados, ya normalizados, y las métricas del rango:

```json
{
  "filtros": {
    "complejo": 4, "fecha_desde": "2026-11-01", "fecha_hasta": "2026-11-30",
    "criterio": "fecha_turno", "cancha_id": null, "deporte_id": null
  },
  "recaudacion": { "total": "1254000.00", "senada": "190000.00" },
  "conteos": {
    "pendientes": 3, "confirmadas": 12, "senadas": 5,
    "canceladas_jugador": 4, "canceladas_complejo": 1, "canceladas_total": 5,
    "ausentes": 2, "completadas": 30
  },
  "ocupacion": [
    { "cancha_id": 7, "cancha": "Cancha 1", "minutos_ofertables": 1200, "minutos_ocupados": 600, "porcentaje": 50.0 }
  ],
  "ranking_horarios": [
    { "hora_inicio": "20:00:00", "reservas": 18 },
    { "hora_inicio": "21:00:00", "reservas": 15 }
  ]
}
```

- `recaudacion.total` suma `precio_acordado` de las reservas confirmadas, señadas y completadas (`2`, `3` y `7`); `recaudacion.senada`, solo las señadas, que también forman parte del total. Los montos van como texto con dos decimales, igual que los precios del resto de la API, y un rango sin reservas devuelve `"0.00"`. Las reservas manuales y las fechas registradas de turnos fijos cuentan igual que las web.
- `conteos` trae la cantidad de reservas de cada estado en el rango, con las canceladas por el jugador (`4`) y por el complejo (`5`) por separado y su suma en `canceladas_total`. Un rango vacío devuelve ceros. Con `criterio=fecha_modificacion`, por ejemplo, responde cuántas reservas se cancelaron en el período, aunque el turno fuera para más adelante.
- `ocupacion` trae una fila por cancha del complejo (con los filtros de cancha y deporte), ordenadas por nombre:
  - **Oferta:** `minutos_ofertables` suma, día por día, los turnos completos que ofrecería la grilla según los horarios de apertura vigentes y la duración del turno, menos los que cierra una excepción activa. Un turno tomado cuenta como ofrecido aunque después se haya cargado un cierre o cambiado el horario.
  - **Ocupado:** `minutos_ocupados` suma la duración de las reservas pendientes, confirmadas, señadas y completadas. Las fechas de turnos fijos cuentan solo si se registraron en la agenda.
  - **Porcentaje:** `porcentaje` es ocupado sobre ofertable, con dos decimales y nunca mayor que 100. Es `null` si la cancha no tiene oferta en el rango.
  - **Canchas sin oferta vigente:** una cancha en mantenimiento, dada de baja o de un deporte dado de baja figura solo si tuvo reservas en el rango, con `minutos_ofertables` y `porcentaje` en `null`.
  - **Criterio:** con `criterio` distinto de `fecha_turno`, `ocupacion` es `null`, porque el rango no describe días de juego.
- `ranking_horarios` trae hasta 10 horarios de inicio, con la cantidad de reservas pendientes, confirmadas, señadas y completadas de cada uno, sumando todas las canchas filtradas. Ordena de mayor a menor y, a igual cantidad, por el horario más temprano. Respeta el `criterio` y un rango sin reservas devuelve `[]`.

## GraphQL

| Método y ruta | Acceso | Uso |
|---|---|---|
| `POST /graphql/` | Público; cada campo aplica sus permisos | `{ "query", "variables" }` en JSON |

- Usa el mismo access token que REST en `Authorization: Bearer <access>`. Igual que en las rutas públicas de REST, un token inválido o vencido no impide consultar los campos públicos.
- Solo admite POST: GET responde `405`.
- Los errores de un campo responden HTTP 200 con `data` en `null` para ese campo y la lista `errors`; cada error lleva el código HTTP equivalente en `extensions.codigo` (`400`, `401`, `403`, `404`, `429`) y, en los de validación, el detalle por campo en `extensions.detalle`. Una consulta mal formada o con campos inexistentes responde `400`.

### `catalogoComplejos`

Mismos complejos, filtros, orden y paginación que `GET /api/complejos/`. Argumentos opcionales: `deporte`, `cobertura`, `servicio` (lista de ids, se exigen todos), `search`, `ordering` y `page`.

```graphql
query {
  catalogoComplejos(deporte: 2, ordering: "precio_desde") {
    count
    results { id nombre direccion latitud longitud precioDesde servicios { id nombre } deportes { id nombre } }
  }
}
```

Cada complejo expone `id`, `nombre`, `direccion`, `latitud`, `longitud`, `telefonoContacto`, `horasLimiteCancelacion`, `infoSena`, `precioDesde`, `servicios` y `deportes`. Los decimales llegan como texto, igual que en REST.

### `misReservas`

Mismas reservas, filtros, orden, paginación y permisos que `GET /api/reservas/mias/`: requiere sesión de jugador (o superadmin). Argumentos opcionales: `estado`, `vigencia` (`proximas` o `pasadas`), `fechaDesde` y `fechaHasta` (`AAAA-MM-DD`), `ordering` y `page`.

```graphql
query {
  misReservas(vigencia: "proximas") {
    count
    results { id complejo { nombre } cancha { nombre } fechaTurno horaInicio estado estadoNombre cancelableHasta }
  }
}
```

- Cada reserva expone los campos de REST en camelCase: `id`, `complejo`, `cancha`, `deporte`, `fechaTurno`, `horaInicio`, `horaFin`, `precioAcordado`, `tipoOcupacion`, `tipoOcupacionNombre`, `estado`, `estadoNombre`, `cancelableHasta` y `fechaCreacion`. Fechas y horas llegan como texto con el mismo formato que REST.
- Sin token, o con un token inválido o vencido, el campo responde `null` con un error `401` y el mismo mensaje que REST; los campos públicos de la misma consulta se resuelven igual. Dueños y operadores reciben `403`.

### `crearReserva` (mutation)

Mismo alta que `POST /api/reservas/`: mismas reglas de turno, anticipación y disponibilidad, mismos errores, mismo límite de altas por cuenta (compartido con REST) y misma auditoría. Argumentos obligatorios: `cancha` (id), `fechaTurno` (`AAAA-MM-DD`) y `horaInicio` (`HH:MM`).

```graphql
mutation {
  crearReserva(cancha: 3, fechaTurno: "2026-11-24", horaInicio: "20:00") {
    reserva { id fechaTurno horaInicio horaFin precioAcordado estado estadoNombre cancelableHasta }
  }
}
```

- Devuelve la reserva creada con los mismos campos que `misReservas`.
- Errores en `extensions.codigo`: `400` (turno inválido, pasado, fuera de la anticipación o complejo no habilitado), `401`, `403`, `409` (turno ocupado, turno fijo o excepción, con el mismo mensaje que REST) y `429`.

## Sistema

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/contratos/` | Superadmin | Contratos; filtros `estado_contrato` (`0` baja, `1` pendiente, `2` activo, `3` suspendido), `estado_propietario`, `propietario`, `search` |
| `GET /api/contratos/<id>/` | Superadmin | Detalle |
| `POST /api/contratos/` | Superadmin | Alta de complejo: `propietario`, `nombre`, `direccion`, `latitud`, `longitud` y opcionales `telefono_contacto`, `horas_limite_cancelacion`, `info_sena`, `estado_contrato` (`1` o `2`) |
| `PATCH /api/contratos/<id>/` | Superadmin | `{ "estado_contrato" }`; con `0` o `3` el complejo deja de publicarse |
| `GET /api/usuarios/` | Superadmin | Cuentas; filtros `rol`, `estado`, `search` |
| `GET /api/usuarios/<id>/` | Superadmin | Detalle |
| `PATCH /api/usuarios/<id>/` | Superadmin | `nombre_completo`, `telefono`, `rol`, `complejo_operado`, `estado` |
| `GET /api/auditoria/` | Superadmin | Registro de eventos de seguridad, filtrable por tipo, usuario, complejo y rango de fechas |
