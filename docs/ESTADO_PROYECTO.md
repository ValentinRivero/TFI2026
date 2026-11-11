# Estado de Implementación del Proyecto — TaLibre

Documento de seguimiento técnico del desarrollo. Cada objetivo completado y verificado se marca con `[x]`.

## Fase 1: Cimientos, Configuración y Modelo de Datos (14 Tablas)
- [x] **1.1.** Estructura inicial de carpetas del monorepo (`backend-django`, `backend-node`, `frontend`, `docs`) y archivo `.gitignore`.
- [x] **1.2.** Configuración de `backend-django/config/settings.py` (conexión PostgreSQL/Supabase, DRF, SimpleJWT, CORS, Channels/Daphne y logging a `security.log`).
- [x] **1.3.** Implementación de `ModeloBase` (borrado lógico `estado = 0`, `fecha_creacion`, `fecha_modificacion`) y las 14 tablas normalizadas con `IntegerChoices` en `core/models.py`.
- [x] **1.4.** Migraciones iniciales aplicadas y comando `seed_inicial.py` (carga de roles, permisos RBAC, deportes, servicios y datos de prueba de Goya).
- [x] **1.5.** Base de calidad y pruebas: tests forzados a SQLite (`config/settings_test.py`), migración a `pytest` + `core/tests/` + cobertura, `core/admin.py` con las 14 tablas sin borrado físico, restricciones de horario (migración `0002`), ajustes de `settings.py` y pipeline de CI base (`.github/workflows/ci.yml`).

## Fase 2: Seguridad, Autenticación JWT y Permisos Jerárquicos
- [x] **2.0.** Rutas base (`core/urls.py`, router), chequeo de salud `GET /api/health/` y `exceptions.py` (`custom_exception_handler`, error 409 de negocio y registro de 403/429).
- [x] **2.1.** Implementación de `throttles.py` (`LoginRateThrottle` 5/min) y `permissions.py` (RBAC + herencia de soporte delegado Superadmin).
- [x] **2.2.** Implementación de `serializers_auth.py` y endpoints de registro (`CU-01`), login/logout JWT con claim `rol`, refresh en cookie HttpOnly y `CORS_ALLOW_CREDENTIALS` (`CU-02`) y perfil propio con baja lógica (`CU-03`).
- [x] **2.3.** Registro dual de auditoría (`logs_auditoria` + `security.log`) y endpoint de consulta de auditoría global para Superadmin (`CU-14`).
- [x] **2.4.** Matriz de permisos por rol verificada con tests, incluyendo el control de rol en altas (`perform_create`) y la respuesta 404 ante complejos ajenos.

## Fase 3: Catálogo, Personalización de Complejos, Canchas y Contratos
- [x] **3.1.** Repositorios, servicios, serializers (con sanitización `nh3`) y vistas para gestión de contratos de complejos por Superadmin (`CU-13`).
- [x] **3.2.** Endpoints públicos de catálogo de complejos activos con filtros dinámicos (deporte, servicios, nombre) y coordenadas para mapa (`CU-04`).
- [x] **3.3.** Endpoints de personalización del complejo (`CU-08`) y ABM lógico de canchas, horarios de apertura y precios (`CU-09`).
- [x] **3.4.** Filtros, búsqueda y orden con `django-filter` (listas blancas) y helper único de sanitización con `nh3`.

## Fase 4: Motor de Grilla, Reservas Atómicas, Excepciones y WebSockets
- [x] **4.1.** Lógica de cálculo de grilla diaria cruzando horarios de apertura, duración por cancha (60/90/120 min), excepciones vigentes y reservas (`CU-05`).
- [x] **4.2.** Gestión de excepciones horarias por día completo o franja horaria, por complejo o por cancha (`CU-11`).
- [x] **4.3.** Motor transaccional de reservas con bloqueo `select_for_update()`, soporte para jugador web (`CU-06`), cancelación con margen horario (`CU-07`), agenda manual telefónica y turnos fijos (`CU-10`).
- [x] **4.4.** Configuración de `routing.py` y `consumers.py` para actualización en tiempo real de casilleros por WebSocket al reservar, cancelar o crear excepción (`RF-15`).
- [x] **4.5.** Channel layer con Redis (`REDIS_URL` opcional, con respaldo en memoria), `ws_auth.py` permisivo con su edición en `asgi.py`, consumer de lectura pública y publicación de eventos con `transaction.on_commit`.
- [x] **4.6.** Test de concurrencia de reservas sobre PostgreSQL en CI (`select_for_update` no bloquea en SQLite).
- [x] **4.7.** Advertencias de conflicto al modificar la operatoria con reservas futuras: editar o dar de baja un rango horario, cambiar `duracion_turno_min` o pasar una cancha a mantenimiento informa las reservas afectadas (409 con el detalle) y solo se aplica con confirmación explícita. Esos cambios, y los de contrato de un complejo, se anuncian a las grillas abiertas por WebSocket.
- [x] **4.8.** Baja de cuenta con reservas: vista previa de lo que se cancela, cancelación de las reservas futuras pendientes y confirmadas, conservación de las señadas o pagadas con aviso urgente al complejo, y baja de los turnos fijos del titular.
- [x] **4.9.** Ajustes de la operatoria de agenda y turnos fijos: reapertura de una reserva cancelada por error, cambio de horario de un turno fijo a otro turno libre (ambos solo por el personal del complejo y con confirmación explícita), y fechas de turnos fijos alcanzadas por una excepción en espera de una decisión del complejo, con aviso, en lugar de rechazar el alta.

## Fase 5: Reportes, GraphQL y Servicio Complementario Node.js
- [x] **5.1.** Endpoint y lógica agregada del Dashboard y Reportes estadísticos filtrables por rangos de fechas (`fecha_turno`, `fecha_creacion`, `fecha_modificacion`), cancha y deporte (`CU-12`).
  - [x] **5.1.1.** Endpoint `GET /api/reportes/dashboard/` con validación de filtros: rango de hasta 366 días, criterio temporal, cancha del complejo y deporte existente; acceso por `ver_reportes` con 404 ante un complejo ajeno o dado de baja.
  - [x] **5.1.2.** Recaudación confirmada o completada (estados `2`, `3` y `7`) y recaudación señada (estado `3`), con ceros en un rango vacío.
  - [x] **5.1.3.** Conteo por estado, con canceladas por el jugador y por el complejo separadas y su subtotal.
  - [x] **5.1.4.** Porcentaje de ocupación por cancha: minutos de reservas ocupantes sobre minutos ofertables (horarios de apertura menos excepciones), solo con el criterio `fecha_turno`.
  - [x] **5.1.5.** Ranking de los horarios más solicitados.
  - [x] **5.1.6.** Cantidad de consultas constante y cierre del punto.
- [x] **5.2.** GraphQL mínimo en `/graphql/` (`core/schema.py`, `core/graphql_views.py`, `config/schema.py`) reutilizando los servicios y permisos de la API REST.
  - [x] **5.2.1.** Endpoint `POST /graphql/` con `JWTGraphQLView` (JWT del encabezado, sin sesión ni CSRF, GraphiQL solo con `DEBUG`) y query pública `catalogoComplejos`, que ejecuta el mismo ViewSet que REST.
  - [x] **5.2.2.** Query `misReservas` con los permisos y filtros del listado de reservas del jugador.
  - [x] **5.2.3.** Mutation `crearReserva` con las mismas validaciones, bloqueos y errores que el alta por REST.
  - [x] **5.2.4.** Profundidad máxima de consulta, límite de campos de primer nivel, introspección apagada fuera de desarrollo y limitador propio del endpoint.
- [x] **5.3.** Base y seguridad de `backend-node`: ES Modules, `app.js`, `server.js`, un router por módulo, Morgan, Helmet, CORS con lista blanca y middlewares `auth`, `rol`, `rateLimit` y `validarCampos`, validando el JWT de Django.
  - [x] **5.3.1.** Proyecto en ES Modules sobre Node 24, `app.js` separado de `server.js`, ruta pública `GET /api/salud`, formato de errores del servicio y pruebas con Jest y Supertest.
  - [x] **5.3.2.** Helmet, CORS con lista blanca, Morgan y limitador global (`rateLimit.middleware.js`).
  - [x] **5.3.3.** `auth.middleware.js`: validación del JWT emitido por Django con la clave compartida (401 sin token, vencido o con firma inválida).
  - [x] **5.3.4.** `rol.middleware.js` y `validarCampos.middleware.js` (403 por rol y 400 con el detalle de validación).
- [x] **5.4.** Persistencia en MongoDB Atlas con Mongoose: `conectarDB`, modelos `Evento` y `Notificacion`, baja lógica y `populate`.
  - [x] **5.4.1.** `conectarDB` (sin credenciales en los logs, filtros saneados contra inyección NoSQL), arranque condicionado a la conexión, plugin de baja lógica que bloquea todo borrado físico y modelo `Evento` con `metadata` validada.
  - [x] **5.4.2.** Modelo `Notificacion` con referencia a `Evento` resuelta por `populate`, categorías, prioridad y destinatario obligatorio.
- [x] **5.5.** Integración Server-to-Server: `djangoClient.service.js` y clima del complejo con Open-Meteo, con manejo de errores 502.
  - [x] **5.5.1.** Django: `GET /api/complejos/<id>/acceso/` para que `backend-node` verifique, reenviando el token del usuario, que administra el complejo (404 si es ajeno).
  - [x] **5.5.2.** `djangoClient.service.js`: cliente HTTP hacia Django con tiempo máximo, reenvío del token y 502 ante fallas.
  - [x] **5.5.3.** `POST /api/actividad`: registro público de visitas y consultas de grilla (tipos 1 y 2) con sesión opcional, limitador estricto y verificación del complejo en Django; "reserva realizada" (tipo 3) queda reservado a Django (5.7).
  - [x] **5.5.4.** Rutas del panel: actividad y bandeja de notificaciones del complejo paginadas de a 20, y cambio de estado, con acceso verificado en Django; bandeja propia de cualquier usuario autenticado, filtrada siempre por el `usuario_id` del token.
  - [x] **5.5.5.** `GET /api/reportes-aux/visitas`: visitas por día del complejo para el dashboard.
  - [x] **5.5.6.** `GET /api/externa/clima/:complejoId`: pronóstico con Open-Meteo a partir de las coordenadas del complejo, con 404 y 502.
- [x] **5.6.** Pruebas de Node con Jest y Supertest (caminos felices y tristes, sin base real) y job de Node en CI.
- [ ] **5.7.** Notificaciones con destinatario (usuario o complejo), categoría y prioridad (normal o urgente), emitidas también por Django mediante una ruta interna de Node autenticada entre servicios.
  - [x] **5.7.1.** Ruta interna de Node para avisos de Django, con clave compartida entre servicios, limitador propio y registro opcional del evento "reserva realizada".
  - [x] **5.7.2.** Entrega real de `AvisoComplejoService` desde Django, con destinatario complejo o usuario, tiempo máximo y registro en el log ante una falla.
  - [ ] **5.7.3.** Eventos y avisos de servidor: reserva realizada (evento tipo 3 y aviso al complejo) y cancelación por el complejo (aviso al jugador).

## Fase 6: Frontend React, PWA y Mapa Interactivo
- [ ] **6.1.** Base React con Vite: capas `services/`, `components/` y `pages/`, `App.jsx` con React Router y `ProtectedRoute`, instancias de Axios con interceptores para ambos backends, `Login`, `Registro` y job de frontend en CI.
- [ ] **6.2.** Vistas del Jugador: `Catalogo`, `ComplejoDetalle` con grilla en vivo (`wsService.js`), clima y reserva, y `MisReservas`.
- [ ] **6.3.** Vistas de Administración: `PanelComplejo`, `GestionCanchas`, `GestionExcepciones`, `Agenda` y `Reportes`; `PanelSistema`, `Contratos` y `Auditoria`.
- [ ] **6.4.** PWA manual (`public/manifest.json`, `public/sw.js`, sin cachear respuestas autenticadas) y mapa interactivo con `react-leaflet` en `MapaComplejos`.
- [ ] **6.5.** Sección de notificaciones para todos los roles; en los paneles de complejo, separada por categoría y con una bandeja de urgentes.

## Fase 7: Despliegue, Pruebas Integrales y Entrega
- [ ] **7.1.** Imágenes Docker (`Dockerfile` y `.dockerignore` por servicio) y `docker-compose.yml` con `web`, `node`, `frontend` y `redis`.
- [ ] **7.2.** Despliegue en VPS: nginx como proxy, HTTPS con dominio, IP real detrás del proxy (`NUM_PROXIES`, `trust proxy`), límite de conexiones WebSocket simultáneas por IP en `/ws/` sin registrar la query string (lleva el token), y `python manage.py check --deploy` sin pendientes.
- [ ] **7.3.** Pruebas de punta a punta de los flujos principales por rol sobre el despliegue.
- [ ] **7.4.** Documentación de entrega: `docs/API.md`, `docs/DECISIONES_ARQUITECTURA.md` y reporte de cobertura (`pytest --cov=core`), con CI en verde y tag `v1.0.0`.

## Notas de la Fase 1
- Modelo de datos alineado a la Sección 3 de `PROJECT.md`: `roles`, `permisos`, `roles_permisos`, `usuarios`, `complejos`, `servicios`, `complejos_servicios`, `deportes`, `canchas`, `horarios_apertura`, `excepciones_horarias`, `turnos_fijos`, `reservas`, `logs_auditoria`.
- El dueño administra su complejo mediante `complejos.propietario_id` y el operador mediante `usuarios.complejo_operado_id`. `usuarios` no tiene `last_login` (por eso `UPDATE_LAST_LOGIN = False` en SimpleJWT).
- `logs_auditoria` usa `fecha_creacion` como fecha de la acción auditada y como referencia de sus filtros: no cambia con una baja lógica, por lo que no hace falta un campo aparte.
- `es_dia_completo` es SMALLINT: `0` = franja horaria, `1` = día completo.
- RBAC con 28 permisos que separan pantallas (`ver_*`) de acciones e incluyen los 8 códigos de ejemplo de la Sección 3 de `PROJECT.md`.
- Pruebas de Fase 1: 27 tests, migrados a `core/tests/` en el punto 1.5.
- Migración `0001` y `seed_inicial` verificados sobre Supabase (PostgreSQL).
- El proyecto no usa `.env.example`: el equipo comparte los `.env` fuera del repositorio.
- La gestión de roles desde una pantalla queda fuera del alcance actual: se reparten permisos entre los 4 roles existentes.
- `config/asgi.py` todavía no tiene su forma definitiva: el punto 4.5 le suma `JWTAuthMiddleware`, y los puntos 4.4 y 4.5 completan `core/routing.py` y `core/consumers.py`.

## Notas del punto 1.5
- Los tests corren siempre sobre SQLite en memoria (`config/settings_test.py`), tanto con `pytest --cov=core` como con `python manage.py test`, y nunca tocan la base de `DATABASE_URL`.
- La migración `0002_restricciones_horarias` agrega `hora_fin > hora_inicio` en reservas y turnos fijos, `hora_cierre > hora_apertura` en horarios de apertura y un único parcial por cancha, fecha y hora de inicio para reservas activas (`1, 2, 3, 7`). Ningún horario puede cerrar pasada la medianoche. Aplicada en Supabase.
- El admin registra las 14 tablas sin borrado físico: solo ofrece la baja lógica, y `logs_auditoria` es de solo lectura.
- El operador ya no tiene `configurar_complejo`: los parámetros comerciales (`info_sena`, `horas_limite_cancelacion`) los editan solo el dueño y el superadmin. Al re-ejecutarse, `seed_inicial` sincroniza `roles_permisos`: las asignaciones que ya no corresponden quedan con `estado = 0` y las vigentes se reactivan. Las consultas de permisos de la Fase 2 deben filtrar asignaciones activas.
- CORS y CSRF apuntan por defecto a Vite (`localhost:5173`). Los `.env` locales se actualizan por fuera del repositorio.
- `.github/workflows/ci.yml` corre `makemigrations --check` y `pytest --cov=core` en cada push y pull request a `main`. Desde la Fase 5 suma el job `node`: `npm ci`, auditoría de dependencias de producción, verificación de sintaxis de `server.js` y `npm run test:cobertura`, que falla por debajo del 95% de cobertura.

## Notas de la Fase 2
- Todos los errores de la API responden `{"error": true, "detail": ...}`; `detail` es un texto o un objeto por campo.
- El login no usa `authenticate()`: `SesionService` distingue email inexistente, contraseña incorrecta y cuenta no activa para la auditoría, y responde lo mismo en los dos primeros casos.
- SimpleJWT 5.5 emite `usuario_id` como texto. `ws_auth.py` y `backend-node` lo convierten a número al leerlo.
- El claim `rol` se arma desde la base en cada login y en cada refresh: un cambio de rol se refleja sin volver a iniciar sesión.
- Logout idempotente: un refresh vencido o ya revocado responde 204 y borra la cookie; solo la ausencia de cookie responde 401.
- La baja de la cuenta propia anonimiza nombre, email, teléfono y contraseña, conserva la fila con `estado = 0` y revoca todos sus refresh tokens. Se rechaza si es la última cuenta de superadmin activa o un dueño con contratos vigentes.
- El registro exige aceptar la política de privacidad: `usuarios` guarda la versión y la fecha aceptadas (migración `0003_consentimiento_politica_privacidad`). Cuando cambia `POLITICA_PRIVACIDAD_VERSION`, el perfil informa `debe_aceptar_politica` y la aceptación se registra con `PATCH /api/perfil/`. Aplicada en Supabase.
- `GET /api/auditoria/` expone `fecha_creacion` como `fecha_accion`.
- La auditoría identifica al titular por `usuario_id` y nunca guarda contraseñas, tokens ni el email tipeado en un login fallido.
- Los 429 se registran una vez por IP, usuario y ruta cada 60 segundos, para que un ataque de fuerza bruta no multiplique las escrituras.
- Registro limitado por IP (`THROTTLE_REGISTRO`, 10 por hora por defecto); login, 5 por minuto.
- `AccesoComplejoMixin` (`core/views.py`) concentra la doble capa de acceso para los recursos de complejo de las fases siguientes.
- Pruebas de Fase 2: 320 tests (362 en total).

## Notas de la Fase 3
- Nuevos endpoints: `/api/deportes/`, `/api/servicios/`, `/api/complejos/` (catálogo, `administrados/`, configuración, `servicios/` y `operadores/`), `/api/canchas/`, `/api/horarios/`, `/api/contratos/` y `/api/usuarios/`.
- El catálogo público solo muestra complejos con `estado = 1` y `estado_contrato = 2`, e ignora el header `Authorization` como el resto de las vistas públicas. Pasar un contrato a Suspendido o Baja lo oculta al instante y el detalle responde 404, sin tocar canchas, reservas ni auditoría; el titular conserva el acceso desde `GET /api/complejos/administrados/`.
- El catálogo no expone al propietario ni ningún dato personal. Servicios y canchas activas se resuelven con un `Prefetch` cada uno y `precio_desde` con una subconsulta: la cantidad de consultas no crece con la cantidad de complejos.
- Filtros por lista blanca en `core/filters.py`: `deporte`, `cobertura` y `servicio` (repetible; se exigen todos), más `search` (nombre y dirección) y `ordering` (`nombre`, `precio_desde`). `deporte` y `cobertura` se exigen sobre la misma cancha activa. Un valor inválido responde 400 y un orden fuera de la lista se ignora.
- `deportes` y `servicios` no paginan: son catálogos maestros chicos y acotados que administra la plataforma.
- `/api/canchas/` y `/api/horarios/` usan `AccesoComplejoMixin`: lo ajeno responde 404, incluso al filtrar por `?complejo=` o `?cancha=` ajenos. El complejo de una cancha y la cancha de un horario se fijan en el alta.
- `administrar_precios` se exige al fijar `precio_base` o `precio_diferenciado`, tanto al editar como al dar de alta: de lo contrario, dar de baja y volver a crear el recurso alcanzaría para cambiar el precio sin el permiso.
- Un día admite varios rangos horarios por cancha (cortes como 08:00 a 12:00 y 16:00 a 23:00), cada uno con su `precio_diferenciado`, siempre que no se superpongan; los rangos contiguos no chocan. La migración `0005_horarios_con_cortes` quita `uq_horario_cancha_dia_activo` y ordena los horarios por `hora_apertura`. Aplicada en Supabase. El solapamiento lo valida `HorarioAperturaService` con la cancha bloqueada (`select_for_update`), que serializa altas y ediciones simultáneas. La grilla del punto 4.1 debe recorrer todos los rangos activos del día.
- Una cancha con reservas activas o turnos fijos vigentes desde hoy en adelante no admite la baja lógica.
- Los nombres de cancha son únicos entre las vigentes del complejo (sin distinguir mayúsculas). Ante un alta simultánea decide la restricción de base y la API responde 400.
- `PUT /api/complejos/<id>/servicios/` deja activos exactamente los servicios pedidos: los quitados pasan a `estado = 0` y los que vuelven se reactivan sobre la misma fila.
- Operadores: el dueño los vincula por email exacto (sin distinguir mayúsculas) y no por id, para que no se puedan recorrer ids en busca de operadores libres y de sus datos de contacto; el superadmin además puede asignarlos desde `PATCH /api/usuarios/<id>/`. Solo se vinculan cuentas activas con rol de operador y sin otro complejo, con un único mensaje de error para cualquier cuenta no disponible. La desvinculación no da de baja la cuenta.
- Contratos: `GET /api/contratos/<id>/` devuelve el detalle. El propietario se informa con su `estado`, y `?estado_propietario=` permite listar contratos vigentes cuyo titular está suspendido o dado de baja: suspender al dueño no suspende el contrato, pero queda a la vista del superadmin.
- Búsqueda (`?search=`) sin distinguir mayúsculas ni tildes en catálogo, contratos y usuarios: «timbos» encuentra «Los Timbós». El lookup `sin_acentos` (`core/filters.py`) usa la extensión `unaccent` en PostgreSQL (migración `0006_extension_unaccent`, aplicada en Supabase) y una función equivalente registrada en SQLite, así las pruebas ejercitan la misma consulta.
- Administración de usuarios: la suspensión o baja administrativa no anonimiza datos personales, pero revoca los refresh tokens vigentes. Una cuenta anonimizada por su titular no admite cambios. Se bloquea con `select_for_update` el conjunto de superadmins activos antes que la fila afectada (el mismo orden que la baja propia, para evitar deadlocks) y se rechaza suspender, dar de baja o cambiar el rol del último superadmin activo. Un dueño con contratos vigentes no cambia de rol, y solo un operador puede tener complejo asignado.
- Auditoría: altas y cambios de contrato (`CAMBIO_CONTRATO`), configuración, servicios y operadores (`CAMBIO_CONFIGURACION`), baja administrativa (`BAJA_USUARIO`) y el nuevo evento `CAMBIO_USUARIO` (16) para suspensión, reactivación, cambio de rol y edición de datos. Registran ids y nombres de campos, nunca los valores escritos. La migración `0004_evento_cambio_usuario` solo actualiza los `choices` de `tipo_evento`. Aplicada en Supabase.
- `limpiar_texto` termina siempre en `nh3.clean(..., tags=set())` cuando agota las pasadas: la salida es un punto fijo de nh3 y conserva escapadas las entidades.
- `docs/API.md` documenta los endpoints vigentes de Django y se amplía en cada fase; el punto 7.4 lo cierra con Node.
- `seed_inicial` y los tests usan solo datos ficticios: emails en dominios reservados (`demo.talibre.test`, `talibre.test`), teléfonos `3777 00xxxx` (inexistentes en la numeración local) y nombres, direcciones, complejos y alias bancarios inventados. Ningún dato de muestra corresponde a personas o comercios reales.
- Pruebas de Fase 3: 282 tests (644 en total).

## Notas de los puntos 4.1 y 4.2
- `GET /api/complejos/<id>/grilla/?fecha=AAAA-MM-DD` es público, ignora el header `Authorization` y no pagina: la grilla de un día está acotada por las canchas del complejo y sus rangos horarios. Responde 404 si el complejo no tiene `estado = 1` y `estado_contrato = 2`, y 400 si falta la fecha, su formato no es ISO o es anterior a hoy.
- Toma las canchas activas (con deporte activo) y recorre todos los rangos activos de `horarios_apertura` del día de la semana de la fecha. Cada rango genera sus bloques por separado según `duracion_turno_min`; un resto menor a un turno completo no se ofrece y un corte no se completa con el rango siguiente. El precio es el `precio_diferenciado` del rango o, si es nulo, el `precio_base` de la cancha.
- Estados de un bloque: `OCUPADO`, `CERRADO_EXCEPCION` (con el `motivo`) o `LIBRE`. La ocupación prevalece sobre la excepción: un turno ya tomado se informa ocupado aunque el complejo cierre después, y queda a la vista para que el complejo lo resuelva.
- Ocupan una reserva en estado `1`, `2`, `3` o `7` y un turno fijo vigente (`estado = 1`) del mismo día de la semana dentro de su vigencia. Si esa fecha ya tiene una reserva generada por el turno fijo, manda el estado de la reserva: cancelar una fecha puntual del turno fijo libera el casillero.
- Todos los cruces son intervalos semiabiertos: una reserva o franja que termina a las 14:00 no ocupa ni cierra el bloque de las 14:00.
- La grilla se calcula con seis consultas fijas, sin importar canchas, reservas ni excepciones. Las ocupaciones se leen solo con columnas de horario (`values()`): los datos de clientes y jugadores no salen de la base, y la respuesta no lleva nombres, teléfonos, emails, observaciones ni la descripción de las excepciones.
- `/api/excepciones/` usa `AccesoComplejoMixin`: lo ajeno responde 404, también al filtrar por `?complejo=` o `?cancha=` ajenos, y un alta en un complejo ajeno, 403. Filtros: `complejo`, `cancha` (incluye las globales de su complejo, que también la cierran), `vigencia` (`vigentes` o `finalizadas`), `fecha` (excepciones que la cubren) y `tipo_motivo`.
- Alta: global (`cancha` nula) o de una cancha activa del mismo complejo; día completo (`es_dia_completo = 1`) sin horas o franja (`es_dia_completo = 0`) con `hora_fin > hora_inicio`. `fecha_inicio` no puede ser anterior a hoy y el rango abarca como máximo 366 días. `creado_por` lo fija el servidor y la `descripcion` se sanitiza con `nh3`.
- Sin edición: una excepción mal cargada se da de baja y se registra otra, así la auditoría conserva cada versión. La baja es lógica y bloquea la fila, así dos bajas simultáneas no se auditan dos veces.
- Alta y baja se auditan (`ALTA_EXCEPCION`, `BAJA_EXCEPCION`) con el id, el alcance, las fechas, el horario y el motivo. La descripción es texto libre del personal y no se replica en la auditoría ni en `security.log`.
- `DifusionGrillaService` es el punto único de aviso a las grillas abiertas. Alta y baja de excepciones ya programan el evento `grilla_actualizada` con `transaction.on_commit`, con `cancha_id` (nulo si es global), `fecha_desde`, `fecha_hasta`, `hora_inicio` y `hora_fin`, sin datos personales. El envío al channel layer se conecta en los puntos 4.4 y 4.5.
- Pruebas de los puntos 4.1 y 4.2: 119 tests (763 en total).

## Notas del punto 4.3
- Nuevos endpoints: `/api/reservas/` (alta web, `mias/` y `cancelar/`), `/api/agenda/` (listado, detalle, alta manual, cambio de estado y `cancelar/`) y `/api/turnos-fijos/` (ABM lógico y `fechas/`).
- Motor anti-colisiones único (`ReservaService.crear_reserva`) para la reserva web y la manual: dentro de `transaction.atomic()` bloquea la fila de la cancha con `select_for_update` y recién entonces valida. Exige complejo con `estado = 1` y `estado_contrato = 2`, cancha activa de deporte activo, un turno que no haya empezado y que `hora_inicio` coincida con un bloque de la grilla de esa fecha. `hora_fin` y `precio_acordado` los fija el servidor (`precio_diferenciado` del rango o `precio_base`); el cliente no puede enviarlos.
- Choques (409, intervalos semiabiertos): reserva en estado `1`, `2`, `3` o `7`; turno fijo vigente de ese día dentro de su vigencia, salvo que la fecha ya tenga su reserva generada; excepción activa global o de la cancha. La restricción `uq_reserva_cancha_turno_activa` queda como última defensa y también responde 409.
- La grilla y el motor comparten las mismas reglas (`DisponibilidadService`): todo bloque `LIBRE` de la grilla se puede reservar. Figura `NO_DISPONIBLE` un bloque libre de hoy que ya empezó o de una fecha posterior a la anticipación máxima.
- Anticipación máxima de 2 meses calendario desde hoy (`MESES_DE_ANTICIPACION_MAXIMA`), para la reserva web y la manual; más allá responde 400 con la última fecha reservable. Los turnos fijos y el registro de sus fechas no tienen ese tope, porque son acuerdos de largo plazo.
- `ReservaRateThrottle` limita las altas web a 20 por hora por cuenta (cuentan también los intentos rechazados) y responde 429; no alcanza a consultas, cancelaciones ni a las altas del personal desde la agenda. Protege al servidor y evita que una cuenta acapare turnos.
- Toda reserva nace en `1` (pendiente de seña). El jugador cancela (`estado = 4`) una reserva propia en `1`, `2` o `3` solo si faltan más horas que `horas_limite_cancelacion`; la respuesta informa `cancelable_hasta`. El complejo cancela (`estado = 5`) sin margen horario.
- Cambios de estado desde la agenda: pendiente a confirmada o señada, confirmada a señada, y cualquiera de ellas a ausente o completada una vez iniciado el turno; ausente y completada se corrigen entre sí. Las canceladas no vuelven atrás y la cancelación tiene su propia ruta.
- `GET /api/reservas/mias/?vigencia=` compara fecha y hora: una reserva es próxima hasta que termina su turno (la de hoy en curso sigue próxima) y pasada desde entonces.
- Un `PATCH` que envía con otro valor un campo que no se edita responde 400 con el motivo y no aplica nada: en la agenda, cancha, fecha, horario y precio; en turnos fijos, cancha, día, horario e inicio de la vigencia. Reenviar el mismo valor no es error, para que un formulario pueda mandar el registro completo. Los campos que calcula el servidor (`hora_fin` de un turno fijo, o `hora_fin`, `precio_acordado` y `estado` en un alta) se siguen ignorando.
- `GET /api/turnos-fijos/?fecha=` trae los turnos fijos vigentes y pausados de ese día; sumando `estado=1`, solo los vigentes.
- La agenda expone el contacto de cada cliente (nombre, teléfono y, si reservó en la web, email) solo a quien administra el complejo; la vista del jugador no incluye las observaciones internas. Las respuestas resuelven sus relaciones con `select_related`: la cantidad de consultas no crece con las reservas.
- Turnos fijos: `hora_fin` según la duración de la cancha y un bloque válido de la grilla; vigencia desde hoy y con al menos una fecha de ese día. Con la cancha bloqueada, se rechaza (409) el choque en cualquier fecha futura de la vigencia con otro turno fijo vigente, una reserva activa o una excepción activa, informando la fecha. Día, horario y cancha no se editan; pausar libera el horario, reanudar revisa toda la vigencia y extender el fin, solo el tramo agregado. El cliente se carga a mano: la API no vincula la cuenta de un jugador.
- `POST /api/turnos-fijos/<id>/fechas/` lleva una fecha puntual del turno fijo a la agenda como reserva confirmada, con el precio de su rango: desde ahí se seña, se completa o se cancela, y cancelarla libera solo ese casillero. Una fecha ya registrada responde 409.
- La baja de un turno fijo es lógica y no toca las fechas ya llevadas a la agenda, que se resuelven como cualquier reserva.
- Alta, cancelación y cambio de estado de reservas se auditan (`RESERVA_CREADA`, `RESERVA_CANCELADA`, `RESERVA_CAMBIO_ESTADO`) con ids, fecha, horario, origen y estados; nunca con nombres, teléfonos ni observaciones.
- Cada alta, cancelación o cambio de ocupación programa `grilla_actualizada` con `transaction.on_commit` en el formato unificado (`fecha_desde = fecha_hasta = fecha_turno` en reservas; la vigencia en turnos fijos, con `fecha_hasta` nulo si no tiene fin).
- Pruebas del punto 4.3: 282 tests (1045 en total). El bloqueo real de `select_for_update` se prueba sobre PostgreSQL en el punto 4.6.
- El punto 4.9 modifica tres reglas de este punto: las canceladas podrán reabrirse, el horario de un turno fijo podrá cambiarse y una excepción dejará de rechazar el alta de un turno fijo.

## Notas de los puntos 4.4 a 4.6
- `ws/complejos/<id>/disponibilidad/` (`core/routing.py`) atiende `DisponibilidadConsumer` (`core/consumers.py`):
  - **Solo lectura:** anónimos y usuarios identificados se unen al grupo `complejo_<id>` y reciben los mismos eventos; los mensajes del cliente se descartan sin decodificarlos.
  - **Rechazo:** un complejo inexistente, dado de baja o sin contrato activo se rechaza en el handshake, con el mismo criterio que el catálogo. El navegador recibe la conexión rechazada (Daphne responde 403); el código `4404` solo es visible dentro de la aplicación ASGI y en las pruebas.
- `config/asgi.py` encadena `AllowedHostsOriginValidator(AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(...))))`. El validador de origen corta antes del handshake las conexiones desde sitios ajenos (Cross-Site WebSocket Hijacking).
- **Identificación permisiva** (`core/ws_auth.py`, `JWTAuthMiddleware`):
  - Lee `?token=<access>`, lo valida con SimpleJWT, convierte el `usuario_id` de texto a entero y carga al usuario solo si está activo.
  - Un token ausente, vencido, inválido, un refresh en lugar de un access o una cuenta no activa dejan `AnonymousUser` y la conexión sigue abierta.
- **Difusión** (`DifusionGrillaService.publicar`): envía al grupo `complejo_<id>` del channel layer desde `transaction.on_commit`, nunca dentro del bloque atómico.
  - **Qué se anuncia:** alta y cancelación de reservas, cambios de ocupación desde la agenda, fechas de turnos fijos, alta, edición y baja de turnos fijos, y alta y baja de excepciones.
  - **Tolerancia a fallas:** si el channel layer falla, el error queda en el logger `core.difusion` y la operación ya confirmada no se revierte. Las grillas se resincronizan por REST al reconectar.
  - **Contexto:** sirve desde código sincrónico (las vistas de DRF, que Daphne ejecuta en un hilo) y desde código asíncrono, donde agenda el envío como tarea en lugar de bloquear el loop y registra igual una falla.
  - **Fuera de este punto:** los cambios de horarios, canchas y contratos todavía no se anuncian; quedan para 4.7.
- **Formato del evento:** se mantiene el unificado del punto 4.2: `{"event": "grilla_actualizada", "cancha_id", "fecha_desde", "fecha_hasta", "hora_inicio", "hora_fin"}`.
  - En una reserva, `fecha_desde = fecha_hasta = fecha_turno`.
  - `cancha_id` es nulo si afecta a todo el complejo.
  - Las horas son nulas en un día completo, y `fecha_hasta` es nula en un turno fijo sin fin.
  - No lleva datos personales.
- **Redis opcional:** con `REDIS_URL`, el channel layer usa `channels_redis` y la caché usa `RedisCache`, así los limitadores comparten contadores entre procesos. Sin ella, ambos quedan en memoria. `config/settings_test.py` los fuerza siempre en memoria. El cliente `redis` queda fijado en `requirements.txt`, porque la caché lo usa en forma directa.
- **Pruebas de WebSocket:** solo usan API pública de Django y Channels. El origen permitido sale de `settings.ALLOWED_HOSTS` y cada prueba arranca con un channel layer limpio redefiniendo `CHANNEL_LAYERS`, que dispara `setting_changed`.
- **Concurrencia** (`core/tests/test_concurrencia.py`, `TransactionTestCase` con hilos reales y barrera):
  - **Casos:** 8 reservas simultáneas del mismo turno (por servicio y por la API) dejan una sola confirmada (201) y el resto en 409. Reservas contra turnos fijos y turnos fijos entre sí también dejan una sola alta. Canchas distintas no se bloquean entre sí.
  - **Dónde corre:** sobre SQLite se saltea. En CI corre en un job aparte (`django-concurrencia`) contra un servicio de PostgreSQL descartable, con `config.settings_concurrencia` y `TEST_POSTGRES_URL`; la suite general sigue en SQLite.
  - **Control:** con el bloqueo de la cancha desactivado, los casos sin restricción de base fallan (turnos fijos duplicados). Eso confirma que los protege `select_for_update` y no la restricción única.
- Pruebas de los puntos 4.4 a 4.6: 37 tests (32 sobre SQLite y 5 de concurrencia sobre PostgreSQL; 1082 en total).

## Notas de los puntos 4.7 y 4.8
- **Advertencias de conflicto** (`ConflictoOperatoriaService`):
  - **Cuándo se revisa:** al editar el día o el horario de un rango, dar de baja un rango, cambiar `duracion_turno_min` o pasar una cancha a mantenimiento. El cálculo corre en la transacción y con la cancha bloqueada (`select_for_update`).
  - **Qué cuenta como afectado:** reservas por jugar (estados `1`, `2` y `3`, sin turnos ya iniciados) y turnos fijos vigentes o pausados que dejarían de coincidir con un bloque de la grilla.
  - **Solo lo nuevo:** se comparan los afectados antes y después del cambio. Pide confirmación lo que el cambio afecta por primera vez o con un motivo distinto (por ejemplo, de fuera de turno a mantenimiento); lo ya marcado y sin novedades no vuelve a frenar otro cambio. Agregar un rango o cambiar solo un precio no puede dejar reservas afuera y no se revisa.
- **Respuesta 409:**
  - **Formato:** `{"error": true, "detail", "requiere_confirmacion": true, "conflictos": {"cantidad", "reservas": [{"id", "fecha_turno", "hora_inicio", "estado"}], "turnos_fijos": [{"id", "dia_semana", "hora_inicio"}]}}`, sin datos personales.
  - **Confirmación:** con `confirmar: true` (en el cuerpo o, en un `DELETE`, en la query string) el cambio se aplica, nada se cancela solo y el cambio confirmado se audita (`CAMBIO_CONFIGURACION`) con los ids afectados.
  - **Baja de cancha:** una cancha con ocupación futura sigue sin poder darse de baja (400), aun con `confirmar`.
- **Marcas en la agenda:** agenda y turnos fijos informan `conflicto_operatoria` (motivo, o nulo) calculado contra los horarios vigentes, y `GET /api/agenda/?con_conflicto=true` lista lo que espera una decisión. La marca desaparece al resolver la reserva o al restituir la operatoria. Los horarios se precargan con un `Prefetch`, así la cantidad de consultas sigue sin crecer con las reservas.
- **Difusión de la operatoria:** alta, edición y baja de canchas y horarios anuncian `grilla_actualizada` para esa cancha desde hoy y sin fin. Reactivar un contrato lo anuncia para todo el complejo. Suspenderlo o darlo de baja cierra las grillas abiertas de ese complejo (código `4404`), en `on_commit`.
- **Vista previa de la baja** (`GET /api/perfil/baja/`): informa reservas a cancelar, señadas que se conservan, turnos fijos a dar de baja, el aviso sobre la conservación del contacto y el impedimento, si lo hay (último superadmin o dueño con contratos vigentes). No modifica nada.
- **Baja de cuenta** (`DELETE /api/perfil/`), en una única transacción y antes de anonimizar:
  - Las reservas por jugar en `1` y `2` pasan a `4` y liberan la grilla en `on_commit`.
  - Las señadas (`3`) se conservan, con una copia del nombre y el teléfono del titular solo en esas filas.
  - Los turnos fijos vigentes y pausados del titular pasan a baja lógica.
  - El historial y las reservas de otros no se tocan.
  - Cada cancelación y el resumen de la baja se auditan sin datos personales.
- **Avisos al complejo** (`AvisoComplejoService`): uno urgente por las señadas conservadas y uno normal por los turnos fijos dados de baja, con ids y sin datos personales. Se entregan en `on_commit` con `robust=True`, así una falla no revierte la baja. Desde el punto 5.7.2 se entregan a la ruta interna de `backend-node`; si no se pueden entregar, quedan en el log del servidor (`core.avisos`).
- **Contacto conservado de la seña:**
  - **Agenda:** muestra la copia y nunca la cuenta anonimizada. Sin copia, el cliente figura como "Titular dado de baja".
  - **Borrado al resolver:** la copia se borra cuando la reserva se resuelve (completada, ausente o cancelada por el complejo).
  - **Plazo máximo:** `python manage.py purgar_contactos_de_bajas`, pensado para correr una vez por día, la borra cuando pasaron más de 30 días desde el turno aunque no se haya resuelto.
- Pruebas de los puntos 4.7 y 4.8: 70 tests. Las suites de reservas, agenda, turnos fijos, conflictos y baja de cuenta pasaron también sobre PostgreSQL.

## Notas del punto 4.9
- **Confirmación explícita:** reapertura y cambio de horario usan el patrón de 4.7. Sin `confirmar: true` responden 409 con `requiere_confirmacion` y una vista previa; con `confirmar: true` se aplican. Los choques reales se validan primero, con la cancha bloqueada, y responden 409 sin opción de confirmar.
- **Reapertura** (`POST /api/agenda/<id>/reabrir/`, `gestionar_agenda`, nunca el jugador):
  - **Qué reabre:** una reserva cancelada (`4` o `5`) de un turno que todavía no empezó vuelve a `1`, `2` o `3`, conservando su precio.
  - **Validación:** revalida el turno como un alta: grilla vigente, cancha y complejo disponibles, sin otra reserva, turno fijo ni excepción en el horario.
  - **Cuentas dadas de baja:** sus reservas no se reabren.
  - **Auditoría y difusión:** se audita como `RESERVA_CAMBIO_ESTADO` ("Reapertura") y se anuncia a la grilla. Funciona también con la fecha cancelada de un turno fijo.
- **Cambio de horario de un turno fijo** (`PATCH` con `hora_inicio`):
  - **Qué se cambia:** el día, la cancha y el inicio de la vigencia siguen fijos. El horario nuevo debe ser un turno de la grilla y `hora_fin` se recalcula.
  - **Validación:** se revisan choques con otros turnos fijos y reservas en toda la vigencia; si el turno está pausado, al reanudarlo.
  - **Vista previa:** informa el horario actual y el nuevo, desde qué fecha rige y las fechas ya registradas, que conservan el horario anterior.
  - **Difusión:** el aviso a la grilla cubre el día completo, para refrescar el horario viejo y el nuevo.
- **Excepciones y turnos fijos:**
  - **Ya no bloquean:** una excepción no rechaza el alta, la reanudación, la extensión ni el cambio de horario de un turno fijo.
  - **Fechas en espera:** las fechas que cubre quedan en espera (`fechas_en_espera` en listado y detalle, filtro `?en_espera=`), siguen ocupando la grilla y se deciden con `fechas/` y `accion` (`mantener` o `cancelar`).
  - **Rendimiento:** el listado las calcula con dos consultas para toda la página.
  - **Aviso:** una excepción nueva que deja fechas en espera genera un aviso urgente al complejo (`AvisoComplejoService`, que entrega a `backend-node` desde el punto 5.7).
- Pruebas del punto 4.9 y del ajuste de la regla de confirmación: 59 tests (1211 en total). Las suites de negocio completas (653 tests) pasaron también sobre PostgreSQL.

## Notas de optimización de la Fase 4
- **Caché de la grilla pública** (`CacheGrillaService`): se cachea la parte que sale de la base, por complejo y fecha.
  - **Vigencia:** la clave lleva una versión por complejo que `DifusionGrillaService` incrementa después de cada commit, antes de avisar por WebSocket, así un cambio confirmado nunca se sirve viejo. La versión se lee antes de calcular, de modo que un cálculo concurrente no se vuelve a servir.
  - **Tiempo de vida:** 60 segundos, para cubrir los cambios que no pasan por la difusión (por ejemplo, el admin de Django).
  - **Marcas del reloj:** las que dependen de la hora (`NO_DISPONIBLE`) se aplican en cada pedido, sobre la copia cacheada.
  - **Si la caché falla:** la grilla se calcula directo de la base.
  - **Efecto:** con N grillas abiertas, un evento cuesta un cálculo y N lecturas de caché, en lugar de N cálculos.
- **Límite propio de la grilla** (`GrillaRateThrottle`, por IP): más amplio que el anónimo general, para no frenar a varios usuarios detrás de una misma IP que recargan con cada evento.
- **Conflictos de la agenda en SQL** (`ReservaRepository.anotar_conflicto_operatoria`): un `Exists` sobre los rangos activos verifica día, rango, alineación y duración del turno. `?con_conflicto=` filtra en la base y la marca se anota en la misma consulta, sin cargar reservas en Python ni armar listas de ids. Un test de paridad compara la regla en SQL con la de Python en SQLite y PostgreSQL.
- **Fechas en espera:** `?en_espera=` prefiltra en SQL los turnos fijos con alguna excepción que los alcanza y solo esos pasan por el cálculo exacto. El aviso de una excepción nueva calcula con esa excepción y los turnos que puede alcanzar.
- **Validación de cambios de operatoria:** lee una sola vez las reservas, los turnos fijos y los horarios (antes, dos veces), y evalúa las dos configuraciones en memoria con los bloques válidos precalculados por día.
- **Sin cambios, porque ya estaban acotados:** motor de reservas, cancelaciones, baja de cuenta, depuración diaria y WebSocket. Los índices existentes cubren las consultas nuevas y no hizo falta migración.
- Pruebas de la optimización: 15 tests (1226 en total). Las suites de negocio (668 tests) pasaron también sobre PostgreSQL.

## Decisiones de arquitectura
- **Frontend:** React con Vite y PWA manual, en capas `services/`, `components/` y `pages/`: solo la capa de servicios conoce las URLs de la API, lo que separa el acceso a datos de la presentación. El access token vive en memoria y el refresh en una cookie HttpOnly, `Secure` y `SameSite=Strict`: un script inyectado por XSS no puede leer el refresh, y `SameSite=Strict` mitiga CSRF. Nada de la sesión se guarda en `localStorage`.
- **`backend-node`:** persiste sus eventos en MongoDB Atlas con Mongoose y consulta a Django por HTTP. No accede a las 14 tablas.
- **WebSocket de disponibilidad:** lectura pública con identificación opcional, porque el catálogo y la grilla son públicos (`CU-04`, `CU-05`). El canal es de solo lectura: no procesa mensajes del cliente, sus eventos no llevan datos personales y rechaza complejos sin contrato activo. La decisión se documenta en `docs/DECISIONES_ARQUITECTURA.md`.
- **Pruebas:** `pytest --cov=core` en Django y `npm test` en Node, ambas en CI.
- **Despliegue:** VPS propio con `docker compose`, nginx y HTTPS.

### Pendientes del equipo
- Instalar Docker Desktop.
- Tener disponible el VPS con dominio antes del 17/11.
