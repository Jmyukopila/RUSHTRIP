# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

RushTrip: planificador de viajes por presupuesto. El usuario escribe ciudades en lenguaje natural, fechas y presupuesto total; el sistema resuelve aeropuertos, busca vuelos + hoteles + coches y devuelve la mejor combinación con links de afiliado (Aviasales, Hotels.nl, Localrent/EconomyBookings).

## Comandos

Hay **dos venvs** en la raíz: `.venv/` (Linux) y `venv/` (Windows). Usa el que corresponda a tu plataforma — en Windows el intérprete que funciona es `venv\Scripts\python.exe`.

```bash
# Backend, Linux (desde la raíz)
.venv/bin/uvicorn main:app --reload --port 8000     # API en :8000, Swagger en /docs
.venv/bin/pytest                                    # tests

# Backend, Windows (PowerShell, desde la raíz)
venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
venv\Scripts\python.exe -m pytest

# Un solo test / archivo / patrón
python -m pytest tests/test_hotels.py                       # un archivo
python -m pytest tests/test_hotels.py::test_calcular_noches # un test
python -m pytest -k "reserva"                               # por patrón de nombre

# Frontend
cd frontend && npm run dev                          # :5173, proxy /api → :8000
cd frontend && npm run build                        # producción → frontend/dist/

# Todo junto
docker compose up --build
```

**Tests:** suite `pytest` (config en `pytest.ini`: `asyncio_mode=auto`, así los tests `async def` corren sin decorador) en `tests/` que cubre la lógica de servicios (hoteles, vuelos), caché, rate limiter y validación de rutas, mockeando la red (sin API keys). `tests/conftest.py` aísla las DBs SQLite (caché y rate limiter) a un dir temporal por test vía `monkeypatch` y expone `FakeResponse` para simular respuestas HTTP — al mockear red, parchea `request_with_retry`/`http_client` con esa clase. No hay linters configurados. Además, verificar cambios con `curl` contra los endpoints y revisando la UI en :5173. La app funciona sin ninguna API key en `.env` (degrada a precios estimados).

## Arquitectura

Tres capas; `services/` y `core/` viven en la **raíz** del repo (no dentro de `backend/`):

- `backend/routes/*.py` — endpoints finos: validan parámetros (fechas `YYYY-MM-DD`, rangos) con `HTTPException` 422 y mensaje en español, y delegan a `services/`. Un router por dominio con `APIRouter(prefix=..., tags=[...])`.
- `services/*.py` — toda la lógica y las llamadas a APIs externas. `services/plan.py::generar_plan()` es el orquestador: resuelve ciudad→IATA (`resolver_iata`), combina vuelos+hoteles+coches, filtra por tier y elige el plan más caro que quepa en el presupuesto.
- `core/` — infraestructura: `http.py` (cliente httpx compartido + `request_with_retry` con backoff, lanza `ExternalAPIError`), `database_cache.py` (caché SQLite WAL en `cache/`: `cache_get` / `cache_get_stale` / `cache_set(key, value, provider, ttl_seconds)`), `cache.py` (TTLCache en memoria), `rate_limiter.py` (límites diarios por IP, persistentes), `errors.py` (jerarquía `AppError`), `config.py` (Pydantic Settings desde `.env`, soporta rotación multi-key `*_2`, `*_3`).
- `main.py` — registra routers, middleware de rate limit (excluye `/health`, `/`, `/docs`, `/openapi.json`), CSP, strip del prefijo `/api` y exception handlers globales que devuelven `{error, code, detail}`.

## Patrón clave: fallback en cascada + precision

Ningún servicio falla hacia el usuario si hay alternativa. Cascada típica: caché → API real → API alternativa → caché vencido (`cache_get_stale`) → datos estimados locales. Toda respuesta de servicio incluye:

- `precision`: calidad del dato (`exacta` | `real` | `mes` | `aproximada` | `parcial` | `stale` | `estimada`; clima usa además `pronostico` | `tipico` | `sin_datos`) — el frontend la muestra como badge (`PrecisionBadge`). `real` = datos reales de proveedor (Hotels.nl); en `plan.py::generar_plan` se normaliza a `exacta` al combinar la precisión de vuelo+hotel.
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
- **Iconos**: SVG inline pequeños, sin emoji (excepto banderas de país en `AirportInput`, generadas por code point). Set compartido en `frontend/src/components/icons.jsx` (`IconWarning`, `IconCheckCircle`, `IconStarRow`, `ACTIVITY_ICON_MAP`, `WEATHER_ICON_MAP`, etc.) — reusar antes de crear uno nuevo. `ACTIVITY_ICON_MAP`/`WEATHER_ICON_MAP` traducen los campos `categoria`/`icono` (emoji) que devuelve el backend a iconos locales; si el backend agrega una categoría o código climático nuevo, sumarlo ahí. No añadir librerías de iconos.
  - **Color de iconos**: los de UI (check, flechas, warning) heredan `currentColor`; los de significado cromático llevan color representativo — un solo tono vía clase en el sitio de uso (hoja CO₂ `text-success`), o multi-tono horneado dentro del SVG para clima (`CLIMA` en `icons.jsx`: sol ámbar, nube gris cálido, lluvia/nieve azul suave `#7BA8C4` — excepción acotada a clima, la paleta no tiene azul).
  - **Tiers metálicos**: los iconos de tier (económico/estándar/premium) usan `MetallicTierIcon` con degradado bronce/plata/oro (`TIER_METAL` en `icons.jsx`), de menos a más brillante. El chip lleva el tinte metálico via `style={{ backgroundColor: TIER_METAL[key].tint }}`. Usar en cualquier vista de tiers (`PlanForm`, `TierComparison`).
  - Hotel = `IconHotel` (edificio), coche = `IconCar` (silueta de auto): iconos reconocibles estilo Lucide para las opciones "Incluir hotel/vehículo" y los renglones del paquete.
- **Resultados = un paquete**: la vista de plan (`PlanResult.jsx`) muestra un único `TripPackage.jsx` (vuelo+hotel+coche como renglones con total y barra de presupuesto); hoteles y coches alternativos van en paneles colapsables "Cambiar hotel/coche" dentro del paquete, no en listas sueltas.
- **Formulario del plan**: `PlanForm.jsx` es un formulario continuo por secciones (no wizard de pasos) en layout de dos columnas con un panel lateral "Tu plan" (`LivePlanPanel`) que refleja los datos en vivo (`lg:sticky`); en móvil el panel colapsa encima del botón de envío. La raíz lleva la clase `plan-form` (usada por `Plan.jsx::handleModify` para el scroll).
- **Estructura JSX**: `export default function Componente({ props })` con destructuring; variantes via prop `variant='default'`; imágenes con fallback `onError`.
- **Textos UI** en español, tono cercano e informativo ("Arma tu viaje", "Dentro de tu presupuesto", "Excede el presupuesto por $X"). Precios con `formatMoney` (separador de miles, sin decimales).
- Mobile-first: base para móvil y ajustes con `sm:`; grids `grid-cols-1 sm:grid-cols-2/3`.

## API y datos

- El contrato completo de los endpoints está en `README.md` (mantenerlo actualizado al cambiar la API).
- Datos auxiliares reusables: `AEROPUERTO_COORDS` en `services/flights.py` (lat/lng de 38 aeropuertos), `CITY_COORDS` en `services/cars.py`, mapeo IATA→ciudad en `services/plan.py`.
- El frontend consume la API solo a través de `frontend/src/api/client.js` (axios, baseURL `/api`, interceptor que traduce errores a español): añadir ahí cualquier función nueva siguiendo el patrón `searchHotels`.
