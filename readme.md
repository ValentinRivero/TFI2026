<div align="center">

# TaLibre

**Plataforma web de gestión y reserva de turnos para complejos deportivos**

Disponibilidad en tiempo real · Mapa interactivo · Panel de gestión para complejos · Reportes

[![CI](https://github.com/ValentinRivero/TFI2026/actions/workflows/ci.yml/badge.svg)](https://github.com/ValentinRivero/TFI2026/actions/workflows/ci.yml) ![Python](https://img.shields.io/badge/Python-3.14-3776AB.svg?logo=python&logoColor=white) ![Django](https://img.shields.io/badge/Django-6.1-092E20.svg?logo=django&logoColor=white) ![Node.js](https://img.shields.io/badge/Node.js-24-5FA04E.svg?logo=nodedotjs&logoColor=white) ![React](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1.svg?logo=postgresql&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg?logo=mongodb&logoColor=white)

</div>

---

## Contexto académico

| | |
|---|---|
| **Institución** | Universidad Tecnológica Nacional (UTN) · Facultad Regional Resistencia · Extensión Áulica Goya |
| **Proyecto** | Trabajo Final Integrador (TFI) de la carrera, integrado con el Trabajo Práctico Integrador (TPI) de Programación IV |
| **Equipo** | Bombo Devs |
| **Integrantes** | Rivero, Santiago Valentín · Villalva, Nahuel Joaquín |
| **Profesor coordinador** | Marco Sosa |
| **Profesores de Programación** | Goya, Juan Manuel · Ramírez, Gerardo |
---

## Sobre el proyecto

En Goya, reservar una cancha suele depender de llamadas o mensajes, sin saber de antemano qué horarios están libres. Los complejos, por su parte, gestionan su agenda en papel o en planillas, y les cuesta medir la ocupación y la recaudación.

**TaLibre** conecta a jugadores y complejos deportivos en una sola plataforma:

- **Jugadores:** buscan complejos por deporte, servicios o cercanía en un mapa, ven la grilla de turnos actualizada en tiempo real, reservan y cancelan desde el celular.
- **Complejos:** configuran sus canchas, horarios y precios, cargan reservas telefónicas y turnos fijos, cierran franjas por mantenimiento o clima y consultan reportes de ocupación y recaudación.

---

## Stack tecnológico

| Capa | Tecnologías |
|---|---|
| Backend principal | Python 3.14, Django 6.1, Django REST Framework, SimpleJWT, Django Channels + Daphne, django-filter, graphene-django, nh3 |
| Servicio complementario | Node.js 24, Express 5, Mongoose 9, Helmet, express-rate-limit, express-validator |
| Frontend | React 19, Vite 8, React Router, Axios, Bootstrap 5, react-leaflet |
| Datos | PostgreSQL (Supabase), MongoDB Atlas, Redis |
| Calidad | pytest + pytest-cov, Jest + Supertest, GitHub Actions |

---

## Flujo de trabajo

- Cada etapa se desarrolla en su propia rama (`feat/<tema>`) y se integra a `main` mediante pull request.
- No se integra nada a `main` sin que el CI quede en verde y sin revisión.
- Los secretos nunca se versionan: los `.env` se comparten por fuera del repositorio.

---

<div align="center">

Desarrollado por **Bombo Devs** · UTN FRRe · Extensión Áulica Goya · 2026

</div>
