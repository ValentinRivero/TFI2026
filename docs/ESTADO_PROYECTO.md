# Estado de Implementación del Proyecto — TaLibre

Documento de seguimiento técnico del desarrollo. Cada objetivo completado y verificado se marca con `[x]` indicando la fecha de cierre.

## Fase 1: Cimientos, Configuración y Modelo de Datos (14 Tablas)
- [x] **1.1.** Estructura inicial de carpetas del monorepo (`backend-django`, `backend-node`, `frontend`, `docs`) y archivo `.gitignore`. — *03/11/2026*
- [x] **1.2.** Configuración de `backend-django/config/settings.py` (conexión PostgreSQL/Supabase, DRF, SimpleJWT, CORS, Channels/Daphne y logging a `security.log`). — *03/11/2026*
- [x] **1.3.** Implementación de `ModeloBase` (borrado lógico `estado = 0`, `fecha_creacion`, `fecha_modificacion`) y las 14 tablas normalizadas con `IntegerChoices` en `core/models.py`. — *04/11/2026*
- [x] **1.4.** Migraciones iniciales aplicadas y comando `seed_inicial.py` (carga de roles, permisos RBAC, deportes, servicios y datos de prueba de Goya). — *04/11/2026*

## Fase 2: Seguridad, Autenticación JWT y Permisos Jerárquicos
- [ ] **2.1.** Implementación de `throttles.py` (`LoginRateThrottle` 5/min), `permissions.py` (RBAC + herencia de soporte delegado Superadmin) y `exceptions.py`.
- [ ] **2.2.** Implementación de `serializers_auth.py` y endpoints de registro (`CU-01`), login/logout JWT (`CU-02`) y perfil propio con baja lógica (`CU-03`).
- [ ] **2.3.** Registro dual de auditoría (`logs_auditoria` + `security.log`) y endpoint de consulta de auditoría global para Superadmin (`CU-14`).

## Fase 3: Catálogo, Personalización de Complejos, Canchas y Contratos
- [ ] **3.1.** Repositorios, servicios, serializers (con sanitización `nh3`) y vistas para gestión de contratos de complejos por Superadmin (`CU-13`).
- [ ] **3.2.** Endpoints públicos de catálogo de complejos activos con filtros dinámicos (deporte, servicios, nombre) y coordenadas para mapa (`CU-04`).
- [ ] **3.3.** Endpoints de personalización del complejo (`CU-08`) y ABM lógico de canchas, horarios de apertura y precios (`CU-09`).

## Fase 4: Motor de Grilla, Reservas Atómicas, Excepciones y WebSockets
- [ ] **4.1.** Lógica de cálculo de grilla diaria cruzando horarios de apertura, duración por cancha (60/90/120 min), excepciones vigentes y reservas (`CU-05`).
- [ ] **4.2.** Gestión de excepciones horarias por día completo o franja horaria, por complejo o por cancha (`CU-11`).
- [ ] **4.3.** Motor transaccional de reservas con bloqueo `select_for_update()`, soporte para jugador web (`CU-06`), cancelación con margen horario (`CU-07`), agenda manual telefónica y turnos fijos (`CU-10`).
- [ ] **4.4.** Configuración de `asgi.py`, `routing.py` y `consumers.py` para actualización en tiempo real de casilleros por WebSocket al reservar, cancelar o crear excepción (`RF-15`).

## Fase 5: Dashboard de Reportes y Servicio Complementario Node.js
- [ ] **5.1.** Endpoint y lógica agregada del Dashboard y Reportes estadísticos filtrables por rangos de fechas (`fecha_turno`, `fecha_creacion`, `fecha_modificacion`), cancha y estado (`CU-12`).
- [ ] **5.2.** Configuración de `backend-node` (`app.js`, `server.js`, middlewares `auth`, `rol`, `rateLimit`, `validarCampos`) validando el JWT de Django.
- [ ] **5.3.** Controladores y servicios en Node.js para registro ágil de actividad/eventos e integración HTTP interna con `backend-django`.

## Fase 6: Frontend PWA, Mapa Interactivo y Pruebas Integrales
- [ ] **6.1.** Estructura base PWA (`manifest.json`, `sw.js`, `styles.css` adaptable móvil/escritorio, `api.js`, `auth.js`, `ws.js`).
- [ ] **6.2.** Vistas del Jugador: Catálogo público con mapa Leaflet (`index.html`), Grilla en vivo y reserva (`complejo.html`), y Mis Reservas (`mis-reservas.html`).
- [ ] **6.3.** Vistas de Administración: Panel del Complejo con agenda manual, canchas, excepciones y gráficos de reportes (`panel-complejo.html`), y Panel del Sistema (`panel-sistema.html`).
- [ ] **6.4.** Pruebas automatizadas en `core/tests.py` y `backend-node/src/tests/`, y scripts de puesta en marcha para el servidor.

## Notas de la Fase 1
- Modelo de datos alineado a la Sección 3 de `PROJECT.md`: `roles`, `permisos`, `roles_permisos`, `usuarios`, `complejos`, `servicios`, `complejos_servicios`, `deportes`, `canchas`, `horarios_apertura`, `excepciones_horarias`, `turnos_fijos`, `reservas`, `logs_auditoria`.
- El dueño administra su complejo mediante `complejos.propietario_id` y el operador mediante `usuarios.complejo_operado_id`. `usuarios` no tiene `last_login` (por eso `UPDATE_LAST_LOGIN = False` en SimpleJWT).
- `logs_auditoria` usa `fecha_creacion` como fecha de la acción auditada y como referencia de sus filtros: no cambia con una baja lógica, por lo que no hace falta un campo aparte.
- `es_dia_completo` es SMALLINT: `0` = franja horaria, `1` = día completo.
- RBAC con 28 permisos que separan pantallas (`ver_*`) de acciones e incluyen los 8 códigos de ejemplo de la Sección 3 de `PROJECT.md`.
- Pruebas de Fase 1 en `core/tests.py` (27 tests en verde).
- Migraciones y `seed_inicial` verificados sobre Supabase (PostgreSQL). Los tests automatizados se ejecutan sobre SQLite.
- El proyecto no usa `.env.example`: el equipo comparte los `.env` fuera del repositorio.
- La gestión de roles desde una pantalla queda fuera del alcance actual: se reparten permisos entre los 4 roles existentes.
- `config/asgi.py` ya quedó con su forma definitiva; en el punto 4.4 solo resta completar `core/routing.py` y `core/consumers.py`.
