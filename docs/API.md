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
| `DELETE /api/perfil/` | Autenticado | Baja de la cuenta propia con anonimización de datos personales (`204`) |

El registro y el inicio de sesión tienen un límite de intentos por origen y responden `429` al superarlo.

## Catálogo público

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/deportes/` | Público | Deportes disponibles (lista completa, sin paginar) |
| `GET /api/servicios/` | Público | Servicios disponibles (lista completa, sin paginar) |
| `GET /api/complejos/` | Público | Complejos habilitados, con coordenadas, servicios, deportes y `precio_desde` |
| `GET /api/complejos/<id>/` | Público | Detalle con sus canchas activas; `404` si el complejo no está habilitado |

Filtros de `GET /api/complejos/`: `deporte` (id), `cobertura` (`1` descubierta, `2` techada, `3` semicubierta), `servicio` (id, repetible: se exigen todos), `search` (nombre o dirección) y `ordering` (`nombre`, `precio_desde`, con `-` para invertir). `deporte` y `cobertura` se cumplen sobre una misma cancha.

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
| `PATCH /api/canchas/<id>/` | Dueño | Cualquier campo salvo `complejo`; `estado` admite `1` o `2` |
| `DELETE /api/canchas/<id>/` | Dueño | Baja; `400` si tiene reservas o turnos fijos vigentes |

### Horarios de apertura

| Método y ruta | Acceso | Uso |
|---|---|---|
| `GET /api/horarios/` | Operador | Rangos vigentes; filtros `cancha` y `dia_semana` (`0` lunes a `6` domingo) |
| `GET /api/horarios/<id>/` | Operador | Detalle |
| `POST /api/horarios/` | Dueño | `cancha`, `dia_semana`, `hora_apertura`, `hora_cierre` (`HH:MM`) y `precio_diferenciado` opcional |
| `PATCH /api/horarios/<id>/` | Dueño | Cualquier campo salvo `cancha` |
| `DELETE /api/horarios/<id>/` | Dueño | Baja del rango |

Un día admite varios rangos por cancha mientras no se superpongan; `hora_cierre` debe ser posterior a `hora_apertura`. Sin `precio_diferenciado` rige el `precio_base` de la cancha.

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
