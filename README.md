# RushTrip ✈️

**Planificador de viajes inteligente por presupuesto.**

Escribí el nombre de tu ciudad de origen y destino, dale un presupuesto total y RushTrip resuelve automáticamente los aeropuertos, busca vuelos, hoteles y autos, y te presenta la mejor combinación ajustada a tu bolsillo.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Frontend | React 18, Vite, Tailwind CSS |
| APIs externas | Travelpayouts (Aviasales), Hotels.nl, Pexels, RapidAPI (coches) |

---

## Funcionalidades

- **Plan por presupuesto** — Escribís el nombre de las ciudades (ej: "Bogotá", "Madrid"), las fechas y tu presupuesto. RushTrip resuelve automáticamente los aeropuertos, busca vuelos, los combina con hoteles reales y te dice cuál es la mejor opción.
- **Resolución automática de aeropuertos** — No necesitás saber códigos IATA. Escribís "Bogotá" y el sistema lo convierte a "BOG" automáticamente. También funciona con códigos IATA si los conocés.
- **Búsqueda de vuelos** — Consulta precios en Travelpayouts con fallback inteligente: si no hay vuelos en la fecha exacta, busca en todo el mes, y si tampoco, muestra los próximos disponibles. Compara conexiones, directos y distintas aerolíneas.
- **Hoteles con fotos y precios reales** — Via Hotels.nl API (datos reales con fotos, precios, ratings). Fallback a precios estimados por destino si no hay API key configurada. Las fotos se complementan con Pexels.
- **Alquiler de coches** — Via RapidAPI con fallback a precios estimados por destino y links de afiliado a Localrent/EconomyBookings.
- **Clima del destino** — Pronóstico real día a día para los días exactos del viaje (Open-Meteo, sin API key). Para fechas a más de 16 días muestra el clima típico calculado con datos históricos reales de años anteriores.
- **Comparativa por tiers** — Al ver los resultados, podés comparar opciones Económico, Estándar y Premium para elegir según tu presupuesto.
- **Frontend responsive** — Interfaz moderna hecha en React + Tailwind con cards, badges, diseño limpio y animaciones suaves.

---

## Estructura del proyecto

```
RUSHTRIP/
├── backend/
│   └── routes/
│       ├── airports.py    # GET /airports/?q=...
│       ├── cars.py        # GET /cars/?ciudad=...
│       ├── flights.py     # GET /flights/?origen=...&destino=...
│       ├── hotels.py      # GET /hotels/?ciudad=...&checkin=...&checkout=...
│       ├── weather.py     # GET /weather/?ciudad=...&fecha_inicio=...&fecha_fin=...
│       └── plan.py        # POST /plan/  ← endpoint principal (acepta nombres de ciudad)
├── core/
│   ├── config.py          # Settings con variables de entorno
│   ├── http.py            # Cliente HTTP reutilizable con retry
│   ├── cache.py           # Utilidades de caché
│   ├── errors.py          # Errores estructurados
│   └── logging.py         # Configuración de Loguru
├── services/
│   ├── flights.py         # Búsqueda de vuelos (Travelpayouts)
│   ├── hotels.py          # Hoteles: Hotels.nl API → precios estimados (fallback)
│   ├── hotels_nl.py       # Integración con Hotels.nl API (datos reales)
│   ├── cars.py            # Coches: RapidAPI → precios estimados (fallback)
│   ├── airports.py        # Autocomplete de aeropuertos + aeropuertos alternativos
│   ├── weather.py         # Clima: pronóstico Open-Meteo → clima típico histórico (fallback)
│   └── plan.py            # Generador de plan de viaje + resolver_iata()
├── frontend/
│   └── src/
│       ├── api/client.js      # Cliente Axios con interceptor de errores
│       ├── components/        # Componentes React
│       │   ├── AirportInput.jsx     # Autocomplete con auto-selección
│       │   ├── PlanForm.jsx         # Formulario progresivo 2 pasos
│       │   ├── PlanResult.jsx       # Resultados con comparativa de tiers
│       │   ├── SummaryCard.jsx      # Resumen del presupuesto
│       │   ├── TierComparison.jsx   # Comparación Económico/Estándar/Premium
│       │   ├── FlightCard.jsx
│       │   ├── HotelCard.jsx
│       │   ├── CarCard.jsx
│       │   └── ...
│       └── pages/
│           ├── Landing.jsx
│           └── Plan.jsx
├── main.py              # Entry point FastAPI (rate limiting, CSP, manejo global de errores)
├── test_api.py          # Tests de integración
└── requirements.txt
```

---

## Quick Start

### 1. Clonar e instalar backend

```bash
git clone https://github.com/JasenovichYukopila/RUSHTRIP.git
cd RUSHTRIP

python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Creá un archivo `.env` en la raíz usando `.env.example` como plantilla:

```env
TRAVELPAYOUTS_TOKEN=tu_token
TRAVELPAYOUTS_MARKER=tu_marker
HOTELSNL_API_KEY=tu_hotelsnl_key
PEXELS_API_KEY=tu_pexels_key
```

- **Travelpayouts** — Registrate en [travelpayouts.com](https://travelpayouts.com) y obtené token + marker desde el panel de APIs. Necesario para vuelos y autocomplete.
- **Hotels.nl** — Registrate en [hotels.nl/api/register.php](https://hotels.nl/api/register.php) (20 segundos, gratis). 200 requests/día. Necesario para hoteles reales.
- **Pexels** — Registrate en [pexels.com/api](https://pexels.com/api) (gratis, 200 req/hora). Para fotos de hoteles.
- **RapidAPI** — Opcional si tenés quota disponible en [RapidAPI](https://rapidapi.com/DataCrawler/api/booking-com15). Usado solo para coches (datos via RapidAPI, sin afiliación directa con Booking.com).

### 3. Iniciar backend

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

La API estará en `http://127.0.0.1:8000`. Documentación interactiva en `http://127.0.0.1:8000/docs`.

### 4. Iniciar frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend arranca en `http://localhost:5173` con proxy automático al backend.

---

## Variables de entorno

| Variable | Requerido | Propósito |
|----------|-----------|-----------|
| `TRAVELPAYOUTS_TOKEN` | Sí | Token de Travelpayouts para vuelos y autocomplete |
| `TRAVELPAYOUTS_MARKER` | Sí | Marker de afiliado Aviasales para comisiones |
| `HOTELSNL_API_KEY` | No* | API key de Hotels.nl para hoteles reales (200 req/día gratis) |
| `PEXELS_API_KEY` | No* | API key de Pexels para fotos de hoteles (200 req/hora gratis) |
| `CORS_ORIGINS` | No | Orígenes CORS separados por coma (default: `http://localhost:5173,http://127.0.0.1:5173`) |

\* Sin `HOTELSNL_API_KEY` los hoteles se muestran como precios estimados. Sin `PEXELS_API_KEY` se usan placehold.co.

---

## API Endpoints

### `POST /plan/` — Generar plan de viaje

`POST /plan/`

Endpoint principal. Recibe **nombres de ciudad** (o códigos IATA), fechas y presupuesto; resuelve aeropuertos automáticamente y devuelve el mejor plan disponible.

**Campos del body:**

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `origen` | string | — | Ciudad o código IATA de origen (ej: `Bogotá`, `BOG`) |
| `destino` | string | — | Ciudad o código IATA de destino (ej: `Madrid`, `MAD`) |
| `fecha_salida` | string | — | Fecha de salida `YYYY-MM-DD` |
| `presupuesto` | number | — | Presupuesto total en USD |
| `pasajeros` | integer | `1` | Número de pasajeros (1-9) |
| `incluir_hotel` | boolean | `true` | Incluir búsqueda de hoteles |
| `incluir_vehiculo` | boolean | `false` | Incluir búsqueda de coches |
| `tier` | string | `"estandar"` | Calidad del viaje: `economico`, `estandar`, `premium` |
| `modo` | string | `"exacto"` | `exacto` requiere `fecha_regreso`; `flexible` usa `duracion_dias` |
| `duracion_dias` | integer | `7` | Duración en días (solo modo `flexible`, 1-14) |

**Request (modo exacto):**
```json
{
  "origen": "Bogotá",
  "destino": "Madrid",
  "fecha_salida": "2026-12-15",
  "fecha_regreso": "2026-12-22",
  "presupuesto": 800,
  "pasajeros": 1,
  "incluir_hotel": true,
  "incluir_vehiculo": false,
  "tier": "estandar",
  "modo": "exacto"
}
```

**Request (modo flexible):**
```json
{
  "origen": "Bogotá",
  "destino": "Madrid",
  "fecha_salida": "2026-12-15",
  "presupuesto": 800,
  "pasajeros": 1,
  "tier": "estandar",
  "modo": "flexible",
  "duracion_dias": 7
}
```

**Response (200):**
```json
{
  "origen": "BOG",
  "destino": "MAD",
  "ciudad_destino": "Madrid",
  "fecha_salida": "2026-12-15",
  "fecha_regreso": "2026-12-22",
  "noches": 7,
  "presupuesto": 800.00,
  "plan_optimo": {
    "vuelo": {
      "origen": "BOG",
      "destino": "MAD",
      "aerolinea": "Air Europa",
      "precio": 320.00,
      "duracion": "9h 30m",
      "escalas": 0,
      "link_compra": "https://www.aviasales.com/search/BOG1512MAD2212?marker=723238"
    },
    "hotel": {
      "nombre": "Hotel Gran Madrid",
      "precio_noche": 55.00,
      "total": 385.00,
      "estrellas": 3,
      "precision": "real"
    },
    "total": 705.00,
    "dentro_presupuesto": true
  },
  "alternativas": [
    {
      "vuelo": { "aerolinea": "Iberia", "precio": 380.00, "escalas": 1 },
      "hotel": { "nombre": "Hotel Europa", "precio_noche": 45.00, "total": 315.00 },
      "total": 695.00,
      "dentro_presupuesto": true
    }
  ],
  "hoteles": [
    {
      "nombre": "Hotel Gran Madrid",
      "precio_noche": 55.00,
      "estrellas": 3,
      "rating": 8.2,
      "foto_url": "https://images.pexels.com/...",
      "amenities": ["wifi", "desayuno", "piscina"],
      "tipo": "real",
      "link_reserva": "https://hotels.nl/booking/hash123"
    }
  ],
  "coches": {
    "coches": [
      {
        "nombre": "Toyota Corolla",
        "tipo": "Compacto",
        "precio_total": 180.00,
        "link_reserva": "https://www.economybookings.com/..."
      }
    ],
    "aviso": "Precios estimados — sin disponibilidad en tiempo real"
  },
  "aeropuertos_alternativos": [
    { "codigo": "BCN", "nombre": "Barcelona-El Prat", "distancia_km": 505 }
  ],
  "clima": {
    "ciudad": "Madrid",
    "dias": [
      { "fecha": "2026-12-15", "temp_max": 12.3, "temp_min": 3.1, "prob_lluvia": 33, "descripcion": "Parcialmente nublado", "icono": "⛅", "tipo": "tipico" }
    ],
    "precision": "tipico",
    "aviso": "Fechas lejanas: mostramos el clima típico de esos días según años anteriores."
  },
  "aviso": null,
  "precision": "exacta"
}
```

**Códigos de error:**

| Código | Significado | Ejemplo |
|--------|-------------|---------|
| `422` | Error de validación | Fecha inválida, origen = destino, tier incorrecto |
| `502` | API externa no disponible | Travelpayouts caído, Hotels.nl sin respuesta |
| `429` | Rate limit excedido | Más de 30 planes/día desde la misma IP |

---

### `GET /flights/` — Buscar vuelos

`GET /flights/?origen=BOG&destino=MIA&fecha_salida=2026-12-15&fecha_regreso=2026-12-22&pasajeros=1`

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `origen` | string | — | Código IATA de origen (ej: `BOG`) |
| `destino` | string | — | Código IATA de destino (ej: `MIA`) |
| `fecha_salida` | string | — | Fecha de salida `YYYY-MM-DD` |
| `fecha_regreso` | string | — | Fecha de regreso `YYYY-MM-DD` (debe ser posterior) |
| `pasajeros` | integer | `1` | Número de pasajeros |

**Response (200):**
```json
{
  "vuelos": [
    {
      "origen": "BOG",
      "destino": "MIA",
      "aerolinea": "American Airlines",
      "precio": 280.00,
      "duracion": "4h 20m",
      "escalas": 0,
      "fecha_salida": "2026-12-15",
      "link_compra": "https://www.aviasales.com/search/BOG1512MIA2212?marker=723238"
    }
  ],
  "aviso": null,
  "precision": "exacta"
}
```

> **Nota:** Si no hay vuelos en la fecha exacta, busca en todo el mes (`precision: "mes"`). Si tampoco, muestra próximos disponibles (`precision: "aproximada"`). Requiere códigos IATA (usar `/airports/` para resolver).

**Validaciones:**
- Fechas deben tener formato `YYYY-MM-DD`
- `fecha_regreso` debe ser posterior a `fecha_salida`
- Rango máximo: 30 días

---

### `GET /hotels/` — Buscar hoteles

`GET /hotels/?ciudad=Miami&checkin=2026-12-15&checkout=2026-12-20&adultos=2`

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `ciudad` | string | — | Nombre de la ciudad (ej: `Miami`, `Bogotá`) |
| `checkin` | string | — | Fecha de entrada `YYYY-MM-DD` |
| `checkout` | string | — | Fecha de salida `YYYY-MM-DD` (posterior a checkin) |
| `adultos` | integer | `2` | Número de adultos |
| `q` | string | `""` | Filtro opcional por nombre de hotel |

**Response (200) — modo real (con HOTELSNL_API_KEY):**
```json
{
  "hoteles": [
    {
      "nombre": "Miami Beach Hotel",
      "precio_noche": 89.50,
      "estrellas": 4,
      "rating": 8.5,
      "foto_url": "https://images.pexels.com/...",
      "amenities": ["wifi", "piscina", "gimnasio"],
      "tipo": "real",
      "link_reserva": "https://hotels.nl/booking/hash456"
    }
  ],
  "aviso": null,
  "ciudad": "Miami",
  "precision": "real"
}
```

**Response (200) — modo estimado (sin HOTELSNL_API_KEY):**
```json
{
  "hoteles": [
    {
      "nombre": "Hotel en Miami (estimado)",
      "precio_noche": 75.00,
      "estrellas": 3,
      "foto_url": "https://via.placeholder.com/400x300",
      "tipo": "estimado",
      "link_reserva": "https://hotels.nl/search?q=Miami"
    }
  ],
  "aviso": "Mostrando precios estimados. Configurá HOTELSNL_API_KEY para datos reales.",
  "ciudad": "Miami",
  "precision": "estimada"
}
```

> **Nota:** Con `HOTELSNL_API_KEY` usa Hotels.nl (datos reales con fotos, ratings, amenities, comisión por reserva). Sin key, devuelve precios de referencia con enlace de búsqueda genérico.

---

### `GET /cars/` — Buscar alquiler de coches

`GET /cars/?ciudad=MIA&pickup_date=2026-12-15&dropoff_date=2026-12-22&pickup_time=10:00&dropoff_time=10:00&driver_age=30&currency=USD`

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `ciudad` | string | — | Código IATA de la ciudad destino |
| `pickup_date` | string | — | Fecha de recogida `YYYY-MM-DD` |
| `dropoff_date` | string | — | Fecha de devolución `YYYY-MM-DD` |
| `pickup_time` | string | `"10:00"` | Hora de recogida `HH:MM` |
| `dropoff_time` | string | `"10:00"` | Hora de devolución `HH:MM` |
| `driver_age` | integer | `30` | Edad del conductor |
| `currency` | string | `"USD"` | Moneda (USD, EUR, COP, etc.) |

**Response (200):**
```json
{
  "coches": [
    {
      "nombre": "Toyota Corolla",
      "tipo": "Compacto",
      "precio_total": 210.00,
      "moneda": "USD",
      "pickup_date": "2026-12-15",
      "dropoff_date": "2026-12-22",
      "proveedor": "Localrent",
      "link_reserva": "https://localrent.com/..."
    }
  ],
  "aviso": "Precios de referencia — la disponibilidad real puede variar"
}
```

> **Nota:** Usa RapidAPI cuando hay quota disponible (datos de Booking.com, sin afiliación). Sin quota, devuelve precios estimados con links de afiliado a Localrent/EconomyBookings.

---

### `GET /airports/` — Autocomplete de aeropuertos

`GET /airports/?q=Madrid`

**Parámetros:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `q` | string | Término de búsqueda (mínimo **2 caracteres**) |

**Response (200):**
```json
[
  { "codigo": "MAD", "nombre": "Madrid-Barajas", "pais": "España" },
  { "codigo": "MAD", "nombre": "Madrid", "pais": "España" },
  { "codigo": "LCG", "nombre": "A Coruña", "pais": "España" }
]
```

> **Nota:** Usa la API pública de Travelpayouts — **no requiere API key**. Sirve tanto para autocomplete en el frontend como para resolución ciudad → IATA en el backend.

---

### `GET /weather/` — Clima del destino

`GET /weather/?ciudad=Madrid&fecha_inicio=2026-06-20&fecha_fin=2026-06-28`

**Parámetros:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `ciudad` | string | Nombre de la ciudad (ej: `Madrid`, `Bogotá`) |
| `fecha_inicio` | string | Primer día `YYYY-MM-DD` |
| `fecha_fin` | string | Último día `YYYY-MM-DD` (rango máximo: 31 días) |

**Response (200):**
```json
{
  "ciudad": "Madrid",
  "lat": 40.4165,
  "lon": -3.70256,
  "fecha_inicio": "2026-06-20",
  "fecha_fin": "2026-06-28",
  "dias": [
    {
      "fecha": "2026-06-20",
      "temp_max": 33.1,
      "temp_min": 19.4,
      "prob_lluvia": 5,
      "codigo": 1,
      "descripcion": "Mayormente despejado",
      "icono": "🌤️",
      "tipo": "pronostico"
    }
  ],
  "precision": "parcial",
  "aviso": "Los días posteriores al 24/06 muestran el clima típico de años anteriores."
}
```

> **Nota:** Usa Open-Meteo — **no requiere API key**. Si las fechas están dentro del horizonte de pronóstico (~16 días) devuelve pronóstico real (`precision: "pronostico"`); para fechas más lejanas devuelve el clima típico de esos días promediando los últimos 3 años de datos históricos reales (`precision: "tipico"`); si el viaje cruza el límite, mezcla ambos (`precision: "parcial"`). Si no hay datos devuelve `dias: []` con `precision: "sin_datos"`. El mismo objeto viene embebido en el campo `clima` de la respuesta de `POST /plan/`.

---

### `GET /min-budget/` — Presupuesto mínimo sugerido

`GET /plan/min-budget/?origen=Bogotá&destino=Madrid&fecha_salida=2026-12-15&fecha_regreso=2026-12-22&pasajeros=1&incluir_hotel=true&incluir_vehiculo=false`

Calcula un presupuesto mínimo usando precios de referencia estáticos — **no hace llamadas a APIs externas**.

**Response (200):**
```json
{
  "presupuesto_minimo": 450.00,
  "desglose": {
    "vuelo": { "minimo": 300, "maximo": 600 },
    "hotel": { "minimo": 35, "maximo": 100 },
    "coche": { "minimo": 25, "maximo": 60 }
  },
  "noches": 7,
  "pasajeros": 1
}
```

---

### `GET /health` — Health check

`GET /health`

```json
{ "status": "ok", "app": "RushTrip API", "version": "1.1.0" }
```

---

### Errores — Formato unificado

Todos los endpoints devuelven errores con esta estructura:

```json
{
  "error": true,
  "code": "validation_error",
  "detail": "Descripción del error específico"
}
```

| Código HTTP | Código interno | Cuándo ocurre |
|-------------|---------------|---------------|
| `422` | `validation_error` | Parámetros inválidos, fechas incorrectas, origen = destino |
| `429` | `rate_limit` | Límite diario excedido (30 planes, 100 búsquedas/IP) |
| `502` | `external_api_error` | API externa (Travelpayouts, Hotels.nl) no responde |
| `500` | `internal_error` | Error inesperado del servidor |

---

### Rate limiting

La API aplica límites diarios por IP (persisten en SQLite, sobreviven reinicios):

| Endpoint | Límite diario/IP |
|----------|-----------------|
| `POST /plan/` | 30 requests |
| `GET /flights/` | 100 requests |
| `GET /hotels/` | 100 requests |
| `GET /cars/` | 100 requests |
| `GET /airports/` | 100 requests |
| `GET /weather/` | 100 requests |
| Otros | 200 requests |

Las respuestas incluyen headers `X-RateLimit-Remaining` y `X-RateLimit-Limit`. Los endpoints `/health`, `/`, `/docs` y `/openapi.json` no están limitados.

---

## Cómo funciona el planificador

1. **Resuelve ciudades a aeropuertos** — El usuario escribe "Bogotá" y "Madrid". El backend usa la API de Travelpayouts para convertirlos a "BOG" y "MAD" automáticamente.
2. **Busca vuelos** — Consulta Travelpayouts para la ruta y fechas dadas. Compara directos, conexiones y distintas aerolíneas. Incluye links de compra con afiliación Aviasales.
3. **Busca hoteles** — Hotels.nl API con datos reales (nombres, fotos, precios, ratings, amenities). Si no hay API key, usa precios estimados por destino. Fotos complementadas con Pexels.
4. **Empareja hotel-plan** — Para cada vuelo, calcula el presupuesto restante y asigna el mejor hotel real que entre en ese monto.
5. **Selecciona óptimo** — Elige el plan cuyo costo total se acerque más al presupuesto sin superarlo. Si ninguno cabe, muestra el más barato disponible.
6. **Busca coches** — Agrega opciones de alquiler en el destino si queda presupuesto con links a Localrent/EconomyBookings.
7. **Comparativa por tiers** — El frontend muestra opciones Económico, Estándar y Premium para que el usuario elija según su presupuesto.

### Estrategia de fallback

| Servicio | Primario | Fallback |
|----------|----------|----------|
| Vuelos | Travelpayouts (fecha exacta) | Travelpayouts (mes) → Travelpayouts (sin fecha) |
| Hoteles | Hotels.nl API (datos reales) | Precios estimados por destino |
| Coches | RapidAPI | Precios estimados por destino |
| Fotos hoteles | Pexels API | Placehold.co |
| Resolución ciudad → IATA | Travelpayouts autocomplete | Cache local |
| Clima | Open-Meteo pronóstico (≤16 días) | Clima típico histórico (3 años) → cache stale |

---

## Despliegue

### Backend (producción)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Recordá actualizar `allow_origins` en `main.py` con tu dominio real.

### Frontend (producción)

```bash
cd frontend
npm run build
# El contenido de frontend/dist/ va a tu CDN o servidor estático
```

---

## Licencia

MIT
