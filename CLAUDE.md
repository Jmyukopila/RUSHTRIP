# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

RushTrip: planificador de viajes por presupuesto. El usuario escribe ciudades en lenguaje natural, fechas y presupuesto total; el sistema resuelve aeropuertos, busca vuelos + hoteles + coches y devuelve la mejor combinación con links de afiliado (Aviasales, Hotels.nl, Localrent/EconomyBookings).

## Comandos

```bash
# Backend (desde la raíz; el venv de Linux es .venv — el dir venv/ es de Windows, ignorarlo)
.venv/bin/uvicorn main:app --reload --port 8000     # API en :8000, Swagger en /docs

# Frontend
cd frontend && npm run dev                          # :5173, proxy /api → :8000
cd frontend && npm run build                        # producción → frontend/dist/

# Todo junto
docker compose up --build
```

**No hay tests ni linters configurados.** Verificar cambios con `curl` contra los endpoints y revisando la UI en :5173. La app funciona sin ninguna API key en `.env` (degrada a precios estimados).

## Arquitectura

Tres capas; `services/` y `core/` viven en la **raíz** del repo (no dentro de `backend/`):

- `backend/routes/*.py` — endpoints finos: validan parámetros (fechas `YYYY-MM-DD`, rangos) con `HTTPException` 422 y mensaje en español, y delegan a `services/`. Un router por dominio con `APIRouter(prefix=..., tags=[...])`.
- `services/*.py` — toda la lógica y las llamadas a APIs externas. `services/plan.py::generar_plan()` es el orquestador: resuelve ciudad→IATA (`resolver_iata`), combina vuelos+hoteles+coches, filtra por tier y elige el plan más caro que quepa en el presupuesto.
- `core/` — infraestructura: `http.py` (cliente httpx compartido + `request_with_retry` con backoff, lanza `ExternalAPIError`), `database_cache.py` (caché SQLite WAL en `cache/`: `cache_get` / `cache_get_stale` / `cache_set(key, value, provider, ttl_seconds)`), `cache.py` (TTLCache en memoria), `rate_limiter.py` (límites diarios por IP, persistentes), `errors.py` (jerarquía `AppError`), `config.py` (Pydantic Settings desde `.env`, soporta rotación multi-key `*_2`, `*_3`).
- `main.py` — registra routers, middleware de rate limit (excluye `/health`, `/`, `/docs`, `/openapi.json`), CSP, strip del prefijo `/api` y exception handlers globales que devuelven `{error, code, detail}`.

## Patrón clave: fallback en cascada + precision

Ningún servicio falla hacia el usuario si hay alternativa. Cascada típica: caché → API real → API alternativa → caché vencido (`cache_get_stale`) → datos estimados locales. Toda respuesta de servicio incluye:

- `precision`: calidad del dato (`exacta` | `mes` | `aproximada` | `parcial` | `stale` | `estimada`) — el frontend la muestra como badge.
- `aviso`: texto opcional en español para el usuario explicando la degradación.

Al añadir un servicio nuevo, replicar este patrón (ver `services/hotels.py` o `services/flights.py` como referencia).

## Convenciones de código

- **Dominio 100% en español**: campos de API (`origen`, `destino`, `fecha_salida`, `precio_noche`), mensajes de error, avisos, docstrings y comentarios.
- Claves de caché con formato `prefijo:param1:param2:...` en minúsculas.
- Dicts de precios/datos de referencia a nivel de módulo con clave `"_default"` para destinos no listados.
- Cada endpoint nuevo requiere tres registros: router en `main.py` (+ tag en `openapi_tags`), entrada en `LIMITS` y prefijo en `_endpoint_group` de `core/rate_limiter.py`.
- Services exponen funciones `async` que devuelven dicts planos (sin modelos Pydantic de salida); los modelos Pydantic solo validan entrada en routes.

## Reglas de diseño web (frontend)

Estética cálida y minimalista — mantenerla en todo componente nuevo:

- **Paleta** (`frontend/tailwind.config.js`): fondo `bg` `#FAF7F2`, cards `card` `#FFF8F0` / blanco, texto `text` `#1A1208`, CTA/énfasis `accent` `#E8611A` (naranja), positivo `success` `#4A7C59`, avisos `warning` `#D4A017`, secundario `muted` `#8C7B6B`, divisores `border` `#E8DDD0`. Usar siempre estos tokens, nunca colores Tailwind genéricos (`blue-500`, etc.).
- **Tipografía**: `font-display` (Playfair Display) solo para títulos; DM Sans (default) para cuerpo; `font-mono` (DM Mono) para todo dato numérico (precios, temperaturas, fechas).
- **Componentes base** (`frontend/src/index.css`): `.card-base` (card blanca con hover lift), `.card-highlight`, `.badge` (xs uppercase), `.btn-primary`, `.btn-outline`, `.input-field`. Reusar antes de inventar clases.
- **Animaciones**: entrada con `animate-fade-slide-up` / `animate-scale-in`, escalonadas entre secciones con `style={{ animationDelay: '...ms', animationFillMode: 'both' }}`; reveal por scroll con el hook `useScrollReveal`.
- **Iconos**: emoji inline (⚠️ ✅ ⭐ 🌱) y SVG inline pequeños. No añadir librerías de iconos.
- **Estructura JSX**: `export default function Componente({ props })` con destructuring; variantes via prop `variant='default'`; imágenes con fallback `onError`.
- **Textos UI** en español, tono cercano e informativo ("Arma tu viaje", "Dentro de tu presupuesto", "Excede el presupuesto por $X"). Precios con `formatMoney` (separador de miles, sin decimales).
- Mobile-first: base para móvil y ajustes con `sm:`; grids `grid-cols-1 sm:grid-cols-2/3`.

## API y datos

- El contrato completo de los endpoints está en `README.md` (mantenerlo actualizado al cambiar la API).
- Datos auxiliares reusables: `AEROPUERTO_COORDS` en `services/flights.py` (lat/lng de 38 aeropuertos), `CITY_COORDS` en `services/cars.py`, mapeo IATA→ciudad en `services/plan.py`.
- El frontend consume la API solo a través de `frontend/src/api/client.js` (axios, baseURL `/api`, interceptor que traduce errores a español): añadir ahí cualquier función nueva siguiendo el patrón `searchHotels`.
