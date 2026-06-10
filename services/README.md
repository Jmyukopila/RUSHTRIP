# Services

Este directorio contiene la lógica de negocio de RushTrip, organizando los servicios por dominio funcional.

## Estructura

```
services/
├── __init__.py     # Paquete
├── airports.py     # Búsqueda de aeropuertos/ciudades + aeropuertos alternativos
├── cars.py         # Alquiler de coches
├── flights.py      # Búsqueda de vuelos
├── hotels.py       # Búsqueda de hoteles (Hotels.nl API → fallback estimado)
├── hotels_nl.py    # Integración con Hotels.nl API (datos reales + comisiones)
└── plan.py         # Generación de planes de viaje + resolución de ciudades
```

## Descripción de Módulos

### airports.py
Busca aeropuertos y ciudades por nombre usando el autocomplete público de Travelpayouts.

**Función principal:**
- `buscar_aeropuerto(texto)` → Devuelve lista de ciudades con código IATA

**Funciones adicionales:**
- `aeropuertos_alternativos(iata)` → Devuelve aeropuertos cercanos (ej: JFK → [LGA, EWR])

**Características:**
- API pública (no requiere autenticación)
- Cache en memoria de 1 hora
- Búsqueda en español
- 40+ grupos de aeropuertos alternativos para áreas metropolitanas

---

### cars.py
Busca opciones de alquiler de coches via RapidAPI.

**Función principal:**
- `buscar_coches(iata, pickup_date, dropoff_date, ...)` → Devuelve lista de coches

**Fuentes de datos:**
1. **Primary:** RapidAPI (datos de Booking.com, sin afiliación)
2. **Fallback:** Precios estimados por ciudad si la API falla

**Coordenadas:** Incluye coordenadas de 40+ ciudades para la búsqueda

---

### flights.py
Busca vuelos usando Travelpayouts API con estrategia de fallback en 3 niveles.

**Función principal:**
- `buscar_vuelos(origen, destino, fecha_salida, fecha_regreso, pasajeros)` → Devuelve lista de vuelos

**Estrategia de búsqueda:**
1. **Nivel 1:** Fecha exacta → Mejor precisión
2. **Nivel 2:** Mes completo → Más cobertura
3. **Nivel 3:** Sin fecha → Próximos disponibles

**Incluye:**
- Mapeo de 15+ aerolineas con descripciones
- URLs de logos de aerolineas
- Links de compra con afiliación
- Estimación de huella de carbono (CO₂) basada en distancia Haversine

---

### hotels.py
Busca hoteles con fallback doble: Hotels.nl API → precios estimados.

**Función principal:**
- `buscar_hoteles(ciudad, checkin, checkout, adultos, estrellas_min, estrellas_max, q)` → Devuelve lista de hoteles

**Fuentes de datos:**
1. **Primary:** Hotels.nl API (datos reales con fotos, precios, ratings, amenities) — requiere `HOTELSNL_API_KEY`
2. **Fallback:** Precios estimados por destino usando tabla de precios de referencia

**Características:**
- Enriquecimiento de fotos vía Pexels API en todos los niveles
- Cache persistente SQLite (24h)
- Links de afiliado a Hotels.nl (comisión por reserva)
- Filtro por estrellas y búsqueda por nombre (`q`)

### hotels_nl.py
Integración con la API REST de Hotels.nl para búsqueda de hoteles reales.

**Docs:** https://hotels.nl/api/

**Función principal:**
- `buscar_hoteles(location, checkin, checkout, currency, persons, language)` → Lista de hoteles normalizados

**Rate limits (free tier):** 200 requests/día, 5 requests/minuto por IP

**Endpoint usado:** `POST /api/search.php` con geocoding automático de ubicación

**Reserva (Hotels.nl):** Usa `/api/booking.php` con `hotelsnl_hash` para iniciar reserva con un clic (requiere cuenta verificada, genera comisión).

---

### plan.py
Genera planes de viaje optimizados combinando vuelos, hoteles y coches. Incluye resolución automática de ciudades a códigos IATA.

**Función principal:**
- `generar_plan(origen, destino, fecha_salida, fecha_regreso, presupuesto, ...)` → Devuelve plan óptimo

**Nueva función:**
- `resolver_iata(texto)` → Convierte nombre de ciudad a código IATA
  - Si el texto ya es IATA (3 letras), lo devuelve directamente
  - Si no, busca en la API de Travelpayouts y toma el primer resultado
  - Cachea resoluciones para evitar llamadas repetidas

**Proceso:**
1. Resuelve ciudades a códigos IATA (si aplica)
2. Busca vuelos disponibles (con fallback en 3 niveles)
3. Si modo=flexible, prueba ventanas de fechas para encontrar la más barata
4. Busca hoteles reales según tier seleccionado
5. Busca coches (opcional)
6. Filtra vuelos por tier (excluye low-cost en premium)
7. Calcula planes para cada vuelo combinado con hotel y coche
8. Empareja con mejores hoteles dentro del presupuesto restante
9. Selecciona plan óptimo (más caro dentro del presupuesto)
10. Busca aeropuertos alternativos cercanos al destino

**Tiers de calidad:**
- `economico`: Hoteles 1-3 estrellas, todas las aerolineas
- `estandar`: Hoteles 3-4 estrellas, todas las aerolineas
- `premium`: Hoteles 4-5 estrellas, excluye low-cost (Spirit, Arajet, Viva, Easyfly)

**Mapeo IATA → Ciudad:** 74+ ciudades principales para convertir códigos IATA a nombres legibles
