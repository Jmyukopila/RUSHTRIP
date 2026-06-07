# services/flights.py
# Servicio de búsqueda de vuelos con cache persistente y fallback a estimación
# Estrategia: cache SQLite → API Travelpayouts → datos estimados locales

import httpx
import logging
import math
import random
from core.config import settings
from core.http import http_client
from core.database_cache import cache_get, cache_get_stale, cache_set

logger = logging.getLogger(__name__)

# Coordenadas (lat, lon) de aeropuertos principales para calculo de distancia
AEROPUERTO_COORDS: dict[str, tuple[float, float]] = {
    "BOG": (4.7016, -74.1469), "MDE": (6.1645, -75.4231),
    "CLO": (3.5432, -76.4993), "CTG": (10.4424, -75.5130),
    "BAQ": (10.8891, -74.7762), "MIA": (25.7932, -80.2906),
    "FLL": (26.0742, -80.1506), "MCO": (28.4312, -81.3080),
    "CUN": (21.0365, -86.8771), "MEX": (19.4363, -99.0721),
    "JFK": (40.6413, -73.7781), "LGA": (40.7772, -73.8726),
    "EWR": (40.6895, -74.1745), "LAX": (33.9416, -118.4085),
    "SFO": (37.6213, -122.3790), "ORD": (41.9742, -87.9073),
    "ATL": (33.6407, -84.4277), "BOS": (42.3656, -71.0096),
    "DCA": (38.8521, -77.0377), "LAS": (36.0840, -115.1537),
    "MAD": (40.4936, -3.5668), "BCN": (41.2974, 2.0833),
    "LHR": (51.4700, -0.4543), "CDG": (49.0097, 2.5479),
    "FCO": (41.8003, 12.2389), "AMS": (52.3105, 4.7683),
    "FRA": (50.0379, 8.5622), "LIS": (38.7813, -9.1359),
    "ZRH": (47.4647, 8.5492), "VIE": (48.1103, 16.5697),
    "GRU": (-23.4356, -46.4731), "EZE": (-34.8222, -58.5358),
    "LIM": (-12.0219, -77.1143), "SCL": (-33.3930, -70.7858),
    "DXB": (25.2532, 55.3657), "SIN": (1.3644, 103.9915),
    "BKK": (13.6900, 100.7501), "HND": (35.5494, 139.7798),
    "NRT": (35.7647, 140.3864), "ICN": (37.4602, 126.4407),
    "SYD": (-33.9399, 151.1753), "MEL": (-37.6690, 144.8410),
}

# Factor de emision: kg CO2 por pasajero-km (promedio vuelos comerciales)
_CO2_KG_PER_PAX_KM = 0.115

# Cache TTL en segundos (6 horas)
_CACHE_TTL = 6 * 3600

# Lista de aerolíneas preferidas para usar en vuelos estimados (las más comunes)
_AEROLINEAS_ESTIMADAS = ["AV", "AA", "LA", "CM", "UA", "DL", "IB", "B6", "AF", "KL"]


def _distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distancia en km entre dos puntos usando formula de Haversine."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimar_co2(origen: str, destino: str) -> float | None:
    """
    Estima la huella de carbono en kg CO2 por pasajero para un vuelo.
    """
    coords_o = AEROPUERTO_COORDS.get(origen.upper())
    coords_d = AEROPUERTO_COORDS.get(destino.upper())
    if not coords_o or not coords_d:
        return None
    km = _distancia_km(*coords_o, *coords_d)
    return round(km * _CO2_KG_PER_PAX_KM, 1)

# Mapeo de códigos IATA de aerolíneas a nombres legibles
AEROLINEAS = {
    "AV": "Avianca",
    "AA": "American Airlines",
    "LA": "LATAM",
    "CM": "Copa Airlines",
    "UA": "United Airlines",
    "DL": "Delta",
    "IB": "Iberia",
    "B6": "JetBlue",
    "NK": "Spirit",
    "AZ": "ITA Airways",
    "AF": "Air France",
    "KL": "KLM",
    "DM": "Arajet",
    "VH": "Viva Air",
    "P5": "EASYFLY",
}

DESCRIPCION_AEROLINEA = {
    "AV": "Aerolínea bandera de Colombia, con hub en Bogotá y más de 70 destinos internacionales.",
    "AA": "American Airlines, una de las mayores aerolíneas de EE.UU., con amplia red de vuelos internacionales.",
    "LA": "LATAM Airlines, líder en América Latina, con vuelos a más de 140 destinos en 25 países.",
    "CM": "Copa Airlines, con hub en Panamá, conecta toda América con uno de los mejores rankings de puntualidad.",
    "UA": "United Airlines, aerolínea global con hubs en Chicago, Newark, Houston y Denver.",
    "DL": "Delta Air Lines, una de las aerolíneas más grandes del mundo, con base en Atlanta.",
    "IB": "Iberia, aerolinea bandera de España, conecta Europa con América Latina.",
    "B6": "JetBlue, aerolinea low-cost de EE.UU. con amplia cobertura y servicio a Latinoamérica.",
    "NK": "Spirit Airlines, aerolinea ultra low-cost de EE.UU., ideal para viajes económicos.",
    "AZ": "ITA Airways, aerolinea bandera de Italia, con hub en Roma y Milán.",
    "AF": "Air France, aerolinea bandera de Francia, con hub en París-Charles de Gaulle.",
    "KL": "KLM, aerolinea bandera de los Países Bajos, con hub en Ámsterdam-Schiphol.",
    "DM": "Arajet, aerolinea dominicana low-cost en expansión por América.",
    "VH": "Viva Air, aerolinea low-cost colombiana con rutas regionales.",
    "P5": "EASYFLY, aerolinea low-cost colombiana de bajo costo.",
}


def logo_aerolinea(iata: str) -> str:
    """Genera URL del logo de una aerolinea usando el servicio avs.io."""
    return f"http://pics.avs.io/100/100/{iata}.png"


def link_compra(link: str, marker: str) -> str:
    """Construye link de compra con marcador de afiliado."""
    sep = "&" if "?" in link else "?"
    return f"https://www.aviasales.com{link}{sep}marker={marker}"


def _mes_desde_fecha(fecha: str) -> str:
    """Extrae el año-mes de una fecha YYYY-MM-DD → YYYY-MM"""
    return fecha[:7]


def _cache_key(origen: str, destino: str, fecha_salida: str, fecha_regreso: str, pasajeros: int) -> str:
    """Genera key única para cache de vuelos."""
    return f"flights:{origen.upper()}:{destino.upper()}:{fecha_salida}:{fecha_regreso}:{pasajeros}"


def _estimar_vuelo(origen: str, destino: str, fecha_salida: str, fecha_regreso: str, pasajeros: int) -> dict:
    """
    Genera vuelos estimados usando datos de referencia cuando la API no está disponible.
    Sin llamadas a APIs externas.

    Args:
        origen: Código IATA de origen
        destino: Código IATA de destino
        fecha_salida: Fecha de salida
        fecha_regreso: Fecha de regreso
        pasajeros: Número de pasajeros

    Returns:
        Dict con vuelos estimados en el mismo formato que la API
    """
    from services.plan import _precio_vuelo_minimo, PRECIO_VUELO_MINIMO

    # Precio base estimado
    precio_base = _precio_vuelo_minimo(destino)
    # Pequeña variación aleatoria para generar variedad
    variacion = random.uniform(0.85, 1.15)
    precio_est = round(precio_base * variacion, 2)

    # Seleccionar aerolínea al azar para cada vuelo
    aerolinea = random.choice(_AEROLINEAS_ESTIMADAS)
    co2_kg = estimar_co2(origen, destino)

    # Estimar duración de vuelo desde distancia
    coords_o = AEROPUERTO_COORDS.get(origen.upper())
    coords_d = AEROPUERTO_COORDS.get(destino.upper())
    if coords_o and coords_d:
        km = _distancia_km(*coords_o, *coords_d)
        duracion_min = int(km / 800 * 60)  # 800 km/h promedio
    else:
        duracion_min = 180  # 3 horas default

    # Generar varios vuelos estimados con diferentes precios/aerolíneas
    vuelos = []
    usadas = set()
    for _ in range(min(6, len(_AEROLINEAS_ESTIMADAS))):
        iata = random.choice(_AEROLINEAS_ESTIMADAS)
        while iata in usadas and len(usadas) < len(_AEROLINEAS_ESTIMADAS):
            iata = random.choice(_AEROLINEAS_ESTIMADAS)
        usadas.add(iata)

        pax_precio = round(precio_est * random.uniform(0.8, 1.2), 2)
        vuelos.append({
            "aerolinea":          iata,
            "aerolinea_nombre":   AEROLINEAS.get(iata, iata),
            "descripcion":        DESCRIPCION_AEROLINEA.get(iata, ""),
            "logo_url":           logo_aerolinea(iata),
            "salida":             fecha_salida,
            "regreso":            fecha_regreso,
            "origen":             origen.upper(),
            "destino":            destino.upper(),
            "duracion_minutos":   duracion_min,
            "escalas":            0,
            "escalas_texto":     "Directo",
            "precio_por_persona": pax_precio,
            "precio_total":       round(pax_precio * pasajeros, 2),
            "pasajeros":          pasajeros,
            "co2_kg":             co2_kg,
            "link_compra":        "",
            "tipo":               "estimado",
        })

    vuelos.sort(key=lambda v: v["precio_por_persona"])

    logger.info(f"Vuelos estimados generados para {origen}→{destino}: {len(vuelos)} opciones, desde ${vuelos[0]['precio_por_persona']:.0f}")

    return {
        "aviso": "Mostrando precios estimados basados en tarifas de referencia. Los precios reales pueden variar.",
        "precision": "estimada",
        "vuelos": vuelos,
    }


async def buscar_vuelos(
    origen: str,
    destino: str,
    fecha_salida: str,
    fecha_regreso: str,
    pasajeros: int = 1,
) -> dict:
    """
    Busca vuelos con estrategia de 4 niveles:
      1. Cache persistente SQLite
      2. Fecha exacta (API)
      3. Mes completo (API)
      4. Datos estimados locales

    Args:
        origen: Codigo IATA del aeropuerto de origen
        destino: Codigo IATA del aeropuerto de destino
        fecha_salida: Fecha de salida en formato YYYY-MM-DD
        fecha_regreso: Fecha de regreso en formato YYYY-MM-DD
        pasajeros: Numero de pasajeros (default: 1)

    Returns:
        Dict con 'aviso', 'vuelos', 'precision'
    """
    key = _cache_key(origen, destino, fecha_salida, fecha_regreso, pasajeros)

    # Nivel 0: Cache persistente
    cached = cache_get(key)
    if cached is not None:
        logger.debug(f"Cache hit para vuelos: {key}")
        return cached

    errores: list[str] = []

    try:
        # Nivel 1: buscar con fechas exactas
        resultado = await _buscar(origen, destino, fecha_salida, fecha_regreso, pasajeros)
        if resultado["vuelos"]:
            resultado["precision"] = "exacta"
            cache_set(key, resultado, provider="travelpayouts", ttl_seconds=_CACHE_TTL)
            return resultado
        if resultado.get("error"):
            errores.append(resultado["error"])

        # Nivel 2: buscar por mes (YYYY-MM) si no hay resultados exactos
        mes_salida  = _mes_desde_fecha(fecha_salida)
        mes_regreso = _mes_desde_fecha(fecha_regreso)
        resultado_mes = await _buscar(origen, destino, mes_salida, mes_regreso, pasajeros)

        if resultado_mes["vuelos"]:
            vuelos_filtrados = [
                v for v in resultado_mes["vuelos"]
                if v.get("salida", "")[:10] >= fecha_salida
            ]
            if vuelos_filtrados:
                primer = vuelos_filtrados[0]
                result = {
                    "aviso": (
                        f"No encontramos vuelos para el {fecha_salida} exacto. "
                        f"Te mostramos las mejores opciones disponibles en {mes_salida}. "
                        f"El mas economico sale el {primer['salida'][:10]}."
                    ),
                    "precision": "mes",
                    "vuelos": vuelos_filtrados,
                }
                cache_set(key, result, provider="travelpayouts", ttl_seconds=_CACHE_TTL)
                return result
            logger.info(f"Vuelos del mes para {origen}->{destino} son todos anteriores a {fecha_salida}, probando nivel 3")
        if resultado_mes.get("error"):
            errores.append(resultado_mes["error"])

        # Nivel 3: buscar proximos disponibles sin filtro de fecha
        resultado_libre = await _buscar(origen, destino, None, None, pasajeros)
        if resultado_libre["vuelos"]:
            primer = resultado_libre["vuelos"][0]
            result = {
                "aviso": (
                    f"No hay vuelos disponibles para {fecha_salida}. "
                    f"El vuelo mas economico disponible sale el {primer['salida'][:10]}. "
                    f"El precio podria variar al momento de reservar."
                ),
                "precision": "aproximada",
                "vuelos": resultado_libre["vuelos"],
            }
            cache_set(key, result, provider="travelpayouts", ttl_seconds=_CACHE_TTL)
            return result
        if resultado_libre.get("error"):
            errores.append(resultado_libre["error"])

        # Si llegamos aquí, la API no devolvió resultados o falló
        # Intentar cache stale (datos expirados son mejor que nada)
        stale = cache_get_stale(key)
        if stale is not None:
            stale["aviso"] = "Mostrando datos de cache previo. Los precios pueden no estar actualizados."
            stale["precision"] = "stale"
            return stale

        # Nivel 4: Fallback a datos estimados locales
        logger.warning(f"API de vuelos no disponible para {origen}→{destino}, usando datos estimados")
        estimados = _estimar_vuelo(origen, destino, fecha_salida, fecha_regreso, pasajeros)
        cache_set(key, estimados, provider="reference", ttl_seconds=_CACHE_TTL)
        return estimados

    except Exception as e:
        logger.error(f"Error buscando vuelos: {e}")
        # Último recurso: cache stale o estimación
        stale = cache_get_stale(key)
        if stale is not None:
            stale["aviso"] = "Mostrando datos de cache previo. Los precios pueden no estar actualizados."
            stale["precision"] = "stale"
            return stale
        estimados = _estimar_vuelo(origen, destino, fecha_salida, fecha_regreso, pasajeros)
        return estimados


async def _buscar(
    origen: str,
    destino: str,
    fecha_salida: str | None,
    fecha_regreso: str | None,
    pasajeros: int,
) -> dict:
    """
    Llamada directa a la API prices_for_dates de Travelpayouts.
    Acepta fechas exactas (YYYY-MM-DD) o por mes (YYYY-MM).
    Si fecha_salida es None, busca próximos disponibles sin filtro.
    """
    # Elegir token (soporte multi-key)
    tokens = settings.travelpayouts_tokens
    if not tokens or not tokens[0]:
        return {"aviso": None, "vuelos": [], "error": "No hay token de Travelpayouts configurado"}

    token = tokens[0]
    params = {
        "origin":      origen.upper(),
        "destination": destino.upper(),
        "token":       token,
        "currency":    "USD",
        "sorting":     "price",
        "limit":       15,
    }

    if fecha_salida:
        params["departure_at"] = fecha_salida
    if fecha_regreso:
        params["return_at"] = fecha_regreso

    try:
        res = await http_client.get(
            "https://api.travelpayouts.com/aviasales/v3/prices_for_dates",
            params=params,
        )
        res.raise_for_status()
        data = res.json()

        logger.debug(f"Respuesta API vuelos [{fecha_salida or 'sin-fecha'}]: {data}")

        if not data.get("success") or not data.get("data"):
            logger.warning(f"Sin datos para {origen}→{destino} [{fecha_salida}]")
            return {"aviso": None, "vuelos": []}

        vuelos = []
        for v in data["data"]:
            iata   = v.get("airline", "??")
            precio = float(v.get("price", 0))
            escalas = v.get("transfers", 0)

            if escalas == 0:
                escalas_texto = "Directo"
            elif escalas == 1:
                escalas_texto = "1 escala"
            else:
                escalas_texto = f"{escalas} escalas"

            co2_por_pax = estimar_co2(origen, destino)
            vuelos.append({
                "aerolinea":          iata,
                "aerolinea_nombre":   AEROLINEAS.get(iata, iata),
                "descripcion":        DESCRIPCION_AEROLINEA.get(iata, ""),
                "logo_url":           logo_aerolinea(iata),
                "salida":             v.get("departure_at", ""),
                "origen":             v.get("origin_airport", origen),
                "destino":            v.get("destination_airport", destino),
                "duracion_minutos":   v.get("duration_to", v.get("duration", 0)),
                "escalas":            escalas,
                "escalas_texto":      escalas_texto,
                "precio_por_persona": precio,
                "precio_total":       round(precio * pasajeros, 2),
                "pasajeros":          pasajeros,
                "co2_kg":             co2_por_pax,
                "link_compra":        link_compra(
                                          v.get("link", ""),
                                          settings.travelpayouts_marker,
                                      ),
            })

        return {
            "aviso":  None,
            "vuelos": sorted(vuelos, key=lambda x: x["precio_por_persona"]),
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP vuelos: {e.response.status_code} - {e.response.text}")
        return {"aviso": None, "vuelos": [], "error": f"Error de API (HTTP {e.response.status_code})"}
    except httpx.RequestError as e:
        logger.error(f"Error de conexion vuelos: {e}")
        return {"aviso": None, "vuelos": [], "error": "Error de conexion con el proveedor de vuelos"}
    except Exception as e:
        logger.error(f"Error inesperado en _buscar: {e}")
        return {"aviso": None, "vuelos": [], "error": "Error inesperado al buscar vuelos"}
