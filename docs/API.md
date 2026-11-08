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
- `estado`: `LIBRE`, `OCUPADO` (reserva activa o turno fijo) o `CERRADO_EXCEPCION`, con el motivo del cierre en `motivo`. Si un turno ya ocupado coincide con un cierre, se informa `OCUPADO`.
- La respuesta no incluye datos de quien reservó.

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
