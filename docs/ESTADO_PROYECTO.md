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
- [ ] **4.3.** Motor transaccional de reservas con bloqueo `select_for_update()`, soporte para jugador web (`CU-06`), cancelación con margen horario (`CU-07`), agenda manual telefónica y turnos fijos (`CU-10`).
- [ ] **4.4.** Configuración de `routing.py` y `consumers.py` para actualización en tiempo real de casilleros por WebSocket al reservar, cancelar o crear excepción (`RF-15`).
- [ ] **4.5.** Channel layer con Redis (`REDIS_URL` opcional, con respaldo en memoria), `ws_auth.py` permisivo con su edición en `asgi.py`, consumer de lectura pública y publicación de eventos con `transaction.on_commit`.
- [ ] **4.6.** Test de concurrencia de reservas sobre PostgreSQL en CI (`select_for_update` no bloquea en SQLite).
- [ ] **4.7.** Advertencias de conflicto al modificar la operatoria con reservas futuras: editar o dar de baja un rango horario, cambiar `duracion_turno_min` o pasar una cancha a mantenimiento informa las reservas afectadas (409 con el detalle) y solo se aplica con confirmación explícita.
- [ ] **4.8.** Baja de cuenta con reservas: vista previa de lo que se cancela, cancelación de las reservas futuras pendientes y confirmadas, conservación de las señadas o pagadas con aviso urgente al complejo, y baja de los turnos fijos del titular.

## Fase 5: Reportes, GraphQL y Servicio Complementario Node.js
- [ ] **5.1.** Endpoint y lógica agregada del Dashboard y Reportes estadísticos filtrables por rangos de fechas (`fecha_turno`, `fecha_creacion`, `fecha_modificacion`), cancha y estado (`CU-12`).
- [ ] **5.2.** GraphQL mínimo en `/graphql/` (`core/schema.py`, `core/graphql_views.py`, `config/schema.py`) reutilizando los servicios y permisos de la API REST.
- [ ] **5.3.** Base y seguridad de `backend-node`: ES Modules, `app.js`, `server.js`, un router por módulo, Morgan, Helmet, CORS con lista blanca y middlewares `auth`, `rol`, `rateLimit` y `validarCampos`, validando el JWT de Django.
- [ ] **5.4.** Persistencia en MongoDB Atlas con Mongoose: `conectarDB`, modelos `Evento` y `Notificacion`, baja lógica y `populate`.
- [ ] **5.5.** Integración Server-to-Server: `djangoClient.service.js` y clima del complejo con Open-Meteo, con manejo de errores 502.
- [ ] **5.6.** Pruebas de Node con Jest y Supertest (caminos felices y tristes, sin base real) y job de Node en CI.
- [ ] **5.7.** Notificaciones con destinatario (usuario o complejo), categoría y prioridad (normal o urgente), emitidas también por Django mediante una ruta interna de Node autenticada entre servicios.

## Fase 6: Frontend React, PWA y Mapa Interactivo
- [ ] **6.1.** Base React con Vite: capas `services/`, `components/` y `pages/`, `App.jsx` con React Router y `ProtectedRoute`, instancias de Axios con interceptores para ambos backends, `Login`, `Registro` y job de frontend en CI.
- [ ] **6.2.** Vistas del Jugador: `Catalogo`, `ComplejoDetalle` con grilla en vivo (`wsService.js`), clima y reserva, y `MisReservas`.
- [ ] **6.3.** Vistas de Administración: `PanelComplejo`, `GestionCanchas`, `GestionExcepciones`, `Agenda` y `Reportes`; `PanelSistema`, `Contratos` y `Auditoria`.
- [ ] **6.4.** PWA manual (`public/manifest.json`, `public/sw.js`, sin cachear respuestas autenticadas) y mapa interactivo con `react-leaflet` en `MapaComplejos`.
- [ ] **6.5.** Sección de notificaciones para todos los roles; en los paneles de complejo, separada por categoría y con una bandeja de urgentes.

## Fase 7: Despliegue, Pruebas Integrales y Entrega
- [ ] **7.1.** Imágenes Docker (`Dockerfile` y `.dockerignore` por servicio) y `docker-compose.yml` con `web`, `node`, `frontend` y `redis`.
- [ ] **7.2.** Despliegue en VPS: nginx como proxy, HTTPS con dominio, IP real detrás del proxy (`NUM_PROXIES`, `trust proxy`) y `python manage.py check --deploy` sin pendientes.
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
- `.github/workflows/ci.yml` corre `makemigrations --check` y `pytest --cov=core` en cada push y pull request a `main`.

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

## Decisiones de arquitectura
- **Frontend:** React con Vite y PWA manual, en capas `services/`, `components/` y `pages/`: solo la capa de servicios conoce las URLs de la API, lo que separa el acceso a datos de la presentación. El access token vive en memoria y el refresh en una cookie HttpOnly, `Secure` y `SameSite=Strict`: un script inyectado por XSS no puede leer el refresh, y `SameSite=Strict` mitiga CSRF. Nada de la sesión se guarda en `localStorage`.
- **`backend-node`:** persiste sus eventos en MongoDB Atlas con Mongoose y consulta a Django por HTTP. No accede a las 14 tablas.
- **WebSocket de disponibilidad:** lectura pública con identificación opcional, porque el catálogo y la grilla son públicos (`CU-04`, `CU-05`). El canal es de solo lectura: no procesa mensajes del cliente, sus eventos no llevan datos personales y rechaza complejos sin contrato activo. La decisión se documenta en `docs/DECISIONES_ARQUITECTURA.md`.
- **Pruebas:** `pytest --cov=core` en Django y `npm test` en Node, ambas en CI.
- **Despliegue:** VPS propio con `docker compose`, nginx y HTTPS.

### Pendientes del equipo
- Instalar Docker Desktop.
- Tener disponible el VPS con dominio antes del 17/11.
