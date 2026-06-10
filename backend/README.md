# Backend / API Routes

Este directorio contiene los endpoints HTTP de la API usando FastAPI.

## Estructura

```
backend/
├── __init__.py    # Paquete
└── routes/
    ├── __init__.py    # Paquete
    ├── airports.py    # GET /airports
    ├── cars.py        # GET /cars
    ├── flights.py     # GET /flights
    ├── hotels.py      # GET /hotels
    └── plan.py        # POST /plan (acepta nombres de ciudad)
```

## Descripción de Endpoints

---

### GET /airports
Busca aeropuertos y ciudades por nombre.

**Query Parameters:**
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `q` | string | Sí | Término de búsqueda (mín 2 chars) |

**Response:**
```json
[
  {
    "nombre": "Bogotá",
    "pais": "Colombia",
    "codigo": "BOG"
  }
]
```

**Errores:**
- `422` - Término muy corto

**Servicio:** `services.airports.buscar_aeropuerto`

---

### GET /flights
Busca vuelos entre dos aeropuertos (requiere códigos IATA).

> **Nota:** Este endpoint es usado internamente por el planificador. Para usuarios finales, usar `POST /plan/` que acepta nombres de ciudad.

**Query Parameters:**
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `origen` | string | Sí | Código IATA origen (ej: BOG) |
| `destino` | string | Sí | Código IATA destino (ej: MIA) |
| `fecha_salida` | string | Sí | Formato YYYY-MM-DD |
| `fecha_regreso` | string | Sí | Formato YYYY-MM-DD |
| `pasajeros` | int | No | Default: 1 |

**Response:**
```json
{
  "aviso": null,
  "precision": "exacta",
  "vuelos": [
    {
      "aerolinea": "AV",
      "aerolinea_nombre": "Avianca",
      "salida": "2026-12-15T08:00:00",
      "precio_por_persona": 250.00,
      "precio_total": 250.00,
      "escalas_texto": "Directo"
    }
  ]
}
```

**Errores:**
- `422` - Fechas inválidas o rango > 30 días

**Servicio:** `services.flights.buscar_vuelos`

---

### GET /hotels
Busca hoteles en una ciudad con datos reales o estimados.

**Query Parameters:**
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `ciudad` | string | Sí | Nombre de ciudad |
| `checkin` | string | Sí | Formato YYYY-MM-DD |
| `checkout` | string | Sí | Formato YYYY-MM-DD |
| `adultos` | int | No | Default: 2 |

**Fuente de datos:**
- **Si `HOTELSNL_API_KEY` configurada:** Hoteles reales con fotos, precios, ratings, amenities vía Hotels.nl API
- **Sin API key:** Hoteles estimados con precios de referencia por destino

**Response (`tipo: "real"` — con Hotels.nl API):**
```json
{
  "aviso": "Precios reales de Hotels.nl. Al reservar generas comision.",
  "ciudad": "Bogota",
  "hoteles": [
    {
      "nombre": "Hotel Port",
      "estrellas": 3,
      "rating": 7.0,
      "reviewScoreWord": "Bien",
      "reviewCount": 150,
      "foto_url": "https://cdn.worldota.net/...",
      "fotos_urls": ["https://cdn.worldota.net/..."],
      "precio_noche": 166.33,
      "precio_total": 499.00,
      "noches": 3,
      "adultos": 2,
      "moneda": "EUR",
      "link_reserva": "https://hotels.nl/search?q=...",
      "hotelsnl_hash": "1584-a0b2c3...",
      "amenities": ["24-hour reception", "Free Wi-Fi"],
      "descripcion": "Hotel Port is located in Rotterdam...",
      "tipo": "real"
    }
  ],
  "precision": "real"
}
```

**Response (`tipo: "estimado"` — fallback sin API key):**
```json
{
  "aviso": "Mostrando precios de referencia...",
  "ciudad": "Miami",
  "hoteles": [
    {
      "nombre": "Hotel Céntrico en Miami",
      "estrellas": 3,
      "rating": 7.5,
      "precio_noche": 108.00,
      "precio_total": 756.00,
      "link_reserva": "https://www.booking.com/searchresults.html?ss=...",
      "tipo": "estimado"
    }
  ],
  "precision": "estimada"
}
```

**Errores:**
- `422` - Fechas inválidas o checkout <= checkin

**Servicio:** `services.hotels.buscar_hoteles`

---

### GET /cars
Busca opciones de alquiler de coches.

**Query Parameters:**
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `ciudad` | string | Sí | Código IATA (ej: MIA) |
| `pickup_date` | string | No | Formato YYYY-MM-DD |
| `dropoff_date` | string | No | Formato YYYY-MM-DD |
| `pickup_time` | string | No | Default: "10:00" |
| `dropoff_time` | string | No | Default: "10:00" |
| `driver_age` | int | No | Default: 30 |
| `currency` | string | No | Default: "USD" |

**Response:**
```json
{
  "ciudad": "MIA",
  "aviso": null,
  "coches": [
    {
      "nombre": "Toyota Corolla",
      "tipo": "Compacto",
      "precio_total": 280.00,
      "link_reserva": "https://www.booking.com/..."
    }
  ]
}
```

**Errores:**
- `422` - Código IATA muy corto

**Servicio:** `services.cars.buscar_coches`

---

### POST /plan
Genera plan de viaje optimizado por presupuesto. **Endpoint principal.**

Acepta **nombres de ciudad** (ej: "Bogotá", "Madrid") o códigos IATA (ej: "BOG", "MAD"). El backend resuelve automáticamente el aeropuerto principal de cada ciudad.

**Request Body:**
```json
{
  "origen": "Bogotá",
  "destino": "Madrid",
  "fecha_salida": "2026-12-15",
  "fecha_regreso": "2026-12-22",
  "presupuesto": 800.00,
  "pasajeros": 1,
  "incluir_hotel": true,
  "incluir_vehiculo": false,
  "tier": "estandar",
  "modo": "exacto",
  "duracion_dias": 7
}
```

**Campos:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `origen` | string | Sí | Ciudad o código IATA de origen |
| `destino` | string | Sí | Ciudad o código IATA de destino |
| `fecha_salida` | string | Sí | Fecha de salida (YYYY-MM-DD) |
| `fecha_regreso` | string | Sí* | Fecha de regreso (YYYY-MM-DD). *No requerida si `modo=flexible` |
| `presupuesto` | float | Sí | Presupuesto total en USD |
| `pasajeros` | int | No | Default: 1 (rango 1-9) |
| `incluir_hotel` | bool | No | Default: true |
| `incluir_vehiculo` | bool | No | Default: false |
| `tier` | string | No | Default: "estandar" (economico, estandar, premium) |
| `modo` | string | No | Default: "exacto" (exacto, flexible) |
| `duracion_dias` | int | No | Default: 7. Solo usado cuando `modo=flexible` |

**Response:**
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
    "vuelo": {...},
    "hotel": {...},
    "coche": {...},
    "total": 750.00,
    "dentro_presupuesto": true
  },
  "alternativas": [...],
  "hoteles": [...],
  "coches": {...},
  "aeropuertos_alternativos": [...],
  "precision": "exacta",
  "aviso": null
}
```

**Errores:**
- `422` - Validación de fechas, rango > 30 días, origen == destino, o no se encontró aeropuerto para la ciudad dada

**Servicio:** `services.plan.generar_plan`

**Resolución de ciudades:**
Internamente, el endpoint llama a `services.plan.resolver_iata()` para:
1. Verificar si el texto ya es un código IATA (3 letras) → usar directamente
2. Si no, buscar en la API de Travelpayouts autocomplete → tomar el primer resultado
3. Cachear la resolución para evitar llamadas repetidas

---

## Validaciones Comunes

Todos los endpoints aplican validaciones:

1. **Fechas:** Formato YYYY-MM-DD, deben ser válidas
2. **Rango:** Máximo 30 días entre salida y regreso
3. **Origen/Destino:** Mínimo 2 caracteres (acepta nombres de ciudad o IATA)
4. **Pasajeros:** Rango 1-9 para el endpoint /plan

## Tags de OpenAPI

Los endpoints están organizados por tags en la documentación:
- `Aeropuertos` - Búsqueda de ciudades/aeropuertos
- `Vuelos` - Búsqueda de vuelos
- `Hoteles` - Búsqueda de hoteles
- `Coches` - Alquiler de vehículos
- `Plan de viaje` - Generación de planes optimizados
