# RushTrip — Contexto del Proyecto

> Planificador de viajes inteligente por presupuesto.
> Resuelve ciudades en lenguaje natural, busca vuelos + hoteles + coches, y devuelve la mejor combinación con links de afiliado.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn, Gunicorn |
| Frontend | React 18, Vite, Tailwind CSS, React Router 6 |
| APIs externas | Travelpayouts, Hotels.nl, Pexels, Open-Meteo, OpenTripMap, RapidAPI |
| Infra | Docker, SQLite (caché + rate limiter), httpx async |
| Deploy | Vercel (serverless via Mangum), Docker compose |

---

## Arquitectura

Tres capas bien definidas:

```
RUSHTRIP/
├── backend/routes/       # Endpoints finos (validación + delegación)
├── services/             # Toda la lógica de negocio y APIs externas
├── core/                 # Infraestructura: HTTP, caché, config, errores, rate limiter
├── frontend/src/         # React + Tailwind (SPA)
├── main.py               # Entry point: registra routers, middleware, exception handlers
└── README.md             # Contrato completo de la API
```

### Patrón clave: fallback en cascada

Cada servicio implementa una cadena de degradación. El usuario nunca ve un error en crudo:

1. Caché SQLite
2. API real
3. API alternativa
4. Caché vencido (`cache_get_stale`)
5. Datos estimados locales (precios de referencia)

Toda respuesta incluye `precision` (exacta, mes, aproximada, parcial, stale, estimada) y `aviso` en español.

---

## Endpoints de la API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/plan/` | POST | Generar plan de viaje (orquestador principal) |
| `/plan/min-budget/` | GET | Presupuesto mínimo sugerido (datos estáticos, sin APIs) |
| `/flights/` | GET | Buscar vuelos por IATA y fechas |
| `/hotels/` | GET | Buscar hoteles por ciudad y fechas |
| `/cars/` | GET | Buscar alquiler de coches |
| `/airports/` | GET | Autocomplete de aeropuertos/ciudades |
| `/weather/` | GET | Clima del destino (Open-Meteo, sin API key) |
| `/activities/` | GET | Actividades del destino (OpenTripMap o curadas) |
| `/health` | GET | Health check |

---

## Frontend — Componentes Principales

| Componente | Propósito |
|---|---|
| `Landing.jsx` | Landing page con hero, búsqueda rápida, cómo funciona |
| `Plan.jsx` | Página principal del planificador |
| `PlanForm.jsx` | Formulario progresivo de 2 pasos (destinos → presupuesto) |
| `AirportInput.jsx` | Autocomplete de aeropuertos con debounce y teclado |
| `PlanResult.jsx` | Visualización completa de resultados del plan |
| `SummaryCard.jsx` | Resumen del viaje con barra de presupuesto |
| `TierComparison.jsx` | Comparativa Económico / Estándar / Premium |
| `FlightCard.jsx` | Card de vuelo con ruta SVG, CO2, link de compra |
| `HotelCard.jsx` | Card de hotel con galería, amenities, precio |
| `CarCard.jsx` | Card de alquiler de coche |
| `WeatherSection.jsx` | Pronóstico día a día con emojis y badges |
| `ActivitiesSection.jsx` | Actividades con precio y links de reserva |
| `SearchWidget.jsx` | Widget embebido de Travelpayouts |
| `Navbar.jsx` | Navbar fijo con progress bar y menú responsive |
| `Footer.jsx` | Footer oscuro con links y contacto |

---

## Timeline del Proyecto

### Fase 1 — Fundación (Abril 2026)

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 28 Abr | `9a9d03c` | Servidor base FastAPI + autocompletado de aeropuertos |
| 28 Abr | `3d8c790` | Gitignore, limpieza de venv y .env |

### Fase 2 — MVP con Travelpayouts (Mayo 2026)

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 3 May | `f5fc5d8` | Initial commit: FastAPI + Travelpayouts, plan de viaje básico |
| 11 May | `b949bb2` | Integración de alquiler de coches (RapidAPI) y hoteles, plan con presupuesto |
| 11 May | `e730de9` | README completo con setup, endpoints y arquitectura |
| 13 May | `4e24b1e` | Documentación del código + READMEs por carpeta |
| 15 May | `6cc7e0c` | **Overhaul grande**: resolución automática ciudad→IATA, rediseño frontend, comparativa de tiers, resiliencia backend |

### Fase 3 — Pulido Frontend (Junio 2026)

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 7 Jun | `3098d3f` | SearchWidget con detección de errores, timeout 15s, aviso localhost |
| 7 Jun | `6e100fd` | Mejoras visuales varias |
| 7 Jun | `d444655` | Mejora estética y actualización en la lógica |
| 7 Jun | `dbbf008` | Fixes a bugs |
| 9 Jun | `1aee098` | Actualización READMEs + implementación Hotels.nl API |
| 9 Jun | `4078779` | Corrección READMEs |
| 9 Jun | `07727b4` | Limpieza de archivos basura |

### Fase 4 — Clima (PR #1 — Junio 2026)

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 10 Jun | `41bb24d` | **Merge PR #1**: Implementación del clima del destino con fechas exactas (Open-Meteo) |
| 10 Jun | `4e1fbc4` | Merge pull request #1 from `pxtroniwnl/feat/clima` |

### Fase 5 — Actividades (PR #2 — Junio 2026)

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 11 Jun | `e68a02c` | Servicio de actividades con OpenTripMap + dataset curado por destino |
| 11 Jun | `e687868` | Endpoint `/activities` + registros (router, rate limit, tags) |
| 11 Jun | `ea52deb` | Actividades integradas en la respuesta del plan |
| 11 Jun | `31f0b0f` | Sección de mejores actividades en resultados del plan (frontend) |
| 11 Jun | `430bd54` | Documentación del contrato `/activities` en README |
| 11 Jun | `bf97699` | **Merge PR #2** desde `Jmyukopila/feat/actividades` |

---

## Estado Actual

- ✅ Servidor base + FastAPI con rate limiting y CORS
- ✅ Autocompletado de aeropuertos (Travelpayouts, sin API key)
- ✅ Resolución automática ciudad → IATA
- ✅ Búsqueda de vuelos con fallback en cascada (4 niveles)
- ✅ Hoteles reales vía Hotels.nl API (con fotos Pexels)
- ✅ Hoteles estimados sin API key
- ✅ Alquiler de coches vía RapidAPI + fallback Localrent/EconomyBookings
- ✅ Plan de viaje con presupuesto (orquestador)
- ✅ Comparativa por tiers (Económico / Estándar / Premium)
- ✅ Clima del destino (Open-Meteo, sin API key)
- ✅ Actividades del destino (OpenTripMap o curadas)
- ✅ Frontend completo con animaciones y diseño responsive
- ✅ Docker multi-stage + docker-compose
- ✅ Deploy en Vercel (serverless con Mangum)
- ✅ Caché persistente SQLite + TTLCache en memoria
- ✅ Multi-key rotation para APIs rate-limitadas

### Por hacer / Mejoras potenciales

- Tests automatizados (no hay linters ni test suite configurados)
- Migración a base de datos (PostgreSQL/Neon)
- Autenticación de usuarios
- Historial de viajes guardados
- Notificaciones de cambios de precio
- Más aerolíneas y destinos en datos de referencia

---

## Cómo iniciar

```bash
# Backend (raíz del repo)
.\venv\Scripts\uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm run dev

# Todo junto
docker compose up --build
```

- API: http://localhost:8000 (docs: /docs)
- Frontend: http://localhost:5173
