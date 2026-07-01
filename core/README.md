# Core

Este directorio contiene las utilidades fundamentales compartidas por toda la aplicación.

## Estructura

```
core/
├── __init__.py    # Paquete
├── cache.py       # Cache TTL simple
├── config.py     # Configuración desde .env
├── http.py       # Cliente HTTP compartido
└── logging.py    # Configuración de logs
```

## Descripción de Módulos

---

### config.py
Gestión centralizada de configuración usando Pydantic Settings.

**Clase:**
- `Settings` - Lee variables de entorno desde `.env`

**Variables de entorno:**
| Variable | Descripción | Default |
|----------|-------------|---------|
| `TRAVELPAYOUTS_TOKEN` | Token para API de vuelos | "" |
| `TRAVELPAYOUTS_MARKER` | ID de afiliado para tracked links | "" |
| `RAPIDAPI_KEY` | API key para RapidAPI (coches) | "" |
| `RAPIDAPI_HOST` | Host de RapidAPI | "booking-com15.p.rapidapi.com" |
| `HOTELSNL_API_KEY` | API key para Hotels.nl (hoteles reales, gratis) | "" |
| `PEXELS_API_KEY` | API key para Pexels (fotos de hoteles) | "" |
| `CORS_ORIGINS` | Orígenes CORS (separados por coma) | "*" |
| `DEBUG` | Modo debug | True |

**Uso:**
```python
from core.config import settings
print(settings.travelpayouts_token)
```

---

### http.py
Cliente HTTP async compartido para reutilizar conexiones.

**Variables:**
- `http_client` - Instancia global con timeout de 10s
- `request_with_retry(method, url, ...)` - Peticion con retry + backoff exponencial (lanza `ExternalAPIError`)

**Uso:**
```python
from core.http import http_client

res = await http_client.get("https://api.example.com/data")
data = res.json()
```

**Beneficios:**
- Conexiones mantenidas vivas (mejor rendimiento)
- Timeout configurable
- Reutilizable en todos los servicios

---

### cache.py
Cache simple con TTL (Time To Live) para funciones async.

**Clase:**
- `TTLCache` - Cache con expiración automática

**Métodos:**
| Método | Descripción |
|--------|-------------|
| `get(key)` | Obtiene valor si existe y no expiró |
| `set(key, value)` | Almacena valor con timestamp actual |
| `get_expired(key)` | Obtiene valor aunque haya expirado (útil para fallback) |
| `clear()` | Limpia todas las entradas |
| `key in cache` | Verifica si clave existe y es válida |

**Usado en:**
- Resolución de ciudades a códigos IATA (`services.plan`)
- Búsqueda de aeropuertos (`services.airports`)
- Precios de referencia de hoteles (`services.hotels`)

**Uso:**
```python
from core.cache import TTLCache

cache = TTLCache(ttl_seconds=300)  # 5 minutos
cache.set("user_123", {"name": "John"})
data = cache.get("user_123")  # None si expiró
```

---

### logging.py
Configuración de logging usando Loguru con salida a consola y archivo.

**Función:**
- `setup_logging()` - Configura todos los handlers de log

**Handlers configurados:**

1. **Consola (stdout):**
   - Formato colorido con timestamp verde
   - Nivel: INFO+
   - Usado para desarrollo

2. **Archivo (rushtrip.log):**
   - Rotación: 10 MB por archivo
   - Retención: 1 semana
   - Nivel: DEBUG (todo se guarda)

3. **Interceptor logging.std:**
   - Redirige logging estándar a Loguru
   - Unifica formato de todos los logs

**Niveles de log:**
- `DEBUG` - Información detallada
- `INFO` - Operaciones normales
- `WARNING` - Problemas menores
- `ERROR` - Errores que afectan funcionalidad
- `CRITICAL` - Fallos totales

**Uso:**
```python
from core.logging import setup_logging
setup_logging()

# En cualquier archivo
import logging
logger = logging.getLogger(__name__)
logger.info("Operación completada")
```