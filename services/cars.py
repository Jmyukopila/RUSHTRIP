# services/cars.py
# Servicio de búsqueda de alquiler de coches via RapidAPI (Booking.com)
# Incluye fallback con precios estimados si la API falla

import httpx
import logging
from datetime import date
from core.config import settings
from core.http import http_client

logger = logging.getLogger(__name__)

# Precios de referencia por día en USD según código IATA de la ciudad
# Usados como fallback cuando la API no responde
PRECIO_REFERENCIA_COCHE: dict[str, float] = {
    # Colombia
    "BOG": 35,  "MDE": 30,  "CLO": 28,  "CTG": 40,  "BAQ": 32,
    # México y Centroamérica
    "MIA": 45,  "CUN": 38,  "MEX": 40,  "GDL": 35,  "LIM": 30,
    # Sudamérica
    "GYE": 25,  "UIO": 28,  "SCL": 35,  "EZE": 40,  "GRU": 38,
    "SDQ": 35,  "HAV": 40,  "PTY": 32,  "SJO": 30,
    # Estados Unidos
    "JFK": 50,  "LAX": 48,  "ORD": 42,  "MCO": 40,  "LAS": 38,
    "SFO": 48,  "BOS": 45,  "WAS": 42,  "ATL": 38,
    # Europa
    "MAD": 35,  "BCN": 35,  "LHR": 50,  "CDG": 48,  "FCO": 40,
    "AMS": 45,  "FRA": 42,  "LIS": 30,  "VIE": 38,  "ZRH": 50,
    "_default": 35,  # Precio por defecto si no está la ciudad
}

# Coordenadas (lat, lng) de las principales ciudades para búsquedas
# Booking.com requiere coordenadas para buscar coches
CITY_COORDS: dict[str, tuple[float, float]] = {
    "BOG": (4.7110, -74.0721),
    "MDE": (6.1646, -75.4225),
    "CLO": (3.5432, -76.4993),
    "CTG": (10.3910, -75.5144),
    "BAQ": (10.8891, -74.7762),
    "MIA": (25.7617, -80.1918),
    "CUN": (21.1619, -86.8515),
    "MEX": (19.4326, -99.1332),
    "GDL": (20.6597, -103.3496),
    "LIM": (-12.0464, -77.0428),
    "GYE": (-2.2037, -79.8972),
    "UIO": (-0.1807, -78.4678),
    "SCL": (-33.4489, -70.6693),
    "EZE": (-34.8222, -58.5358),
    "GRU": (-23.5505, -46.6333),
    "SDQ": (18.4861, -69.9312),
    "HAV": (23.1136, -82.3666),
    "PTY": (8.9824, -79.5199),
    "SJO": (9.9281, -84.0907),
    "JFK": (40.7128, -74.0060),
    "LAX": (34.0522, -118.2437),
    "ORD": (41.8781, -87.6298),
    "MCO": (28.5383, -81.3792),
    "LAS": (36.1699, -115.1398),
    "SFO": (37.7749, -122.4194),
    "BOS": (42.3601, -71.0589),
    "WAS": (38.9072, -77.0369),
    "ATL": (33.7490, -84.3880),
    "MAD": (40.4168, -3.7038),
    "BCN": (41.3874, 2.1686),
    "LHR": (51.5074, -0.1278),
    "CDG": (48.8566, 2.3522),
    "FCO": (41.9028, 12.4964),
    "AMS": (52.3676, 4.9041),
    "FRA": (50.1109, 8.6821),
    "LIS": (38.7223, -9.1393),
    "VIE": (48.2082, 16.3738),
    "ZRH": (47.3769, 8.5417),
    "_default": (40.7128, -74.0060),  # NYC por defecto
}


def _get_coords(iata: str) -> tuple[float, float]:
    """Obtiene coordenadas (lat, lng) para un código IATA de ciudad."""
    return CITY_COORDS.get(iata.upper(), CITY_COORDS["_default"])


def _precio_coche_referencia(iata: str) -> float:
    """Obtiene el precio de referencia por día para una ciudad."""
    return PRECIO_REFERENCIA_COCHE.get(iata.upper(), PRECIO_REFERENCIA_COCHE["_default"])


def _calcular_dias(pickup_date: str | None, dropoff_date: str | None) -> int:
    """Calcula el número de días de alquiler. Mínimo 1 día."""
    if pickup_date and dropoff_date:
        return max((date.fromisoformat(dropoff_date) - date.fromisoformat(pickup_date)).days, 1)
    return 7  # Por defecto 7 días


def _generar_fallback(iata: str, pickup_date: str | None, dropoff_date: str | None) -> dict:
    """
    Genera datos de fallback con precios estimados cuando la API falla.
    Incluye 4 categorias de vehiculos con precios relativos.
    """
    dias = _calcular_dias(pickup_date, dropoff_date)
    precio_dia = _precio_coche_referencia(iata)
    precio_total = round(precio_dia * dias, 2)
    lat, lng = _get_coords(iata)
    pickup = pickup_date or ""
    dropoff = dropoff_date or ""

    link_base = (
        f"https://www.booking.com/cars/search?"
        f"lat={lat}&lng={lng}&pickupDate={pickup}&dropoffDate={dropoff}"
        f"&currency=USD"
    )

    # Links de afiliados para coches
    link_localrent = f"https://localrent.tpo.li/Gfm1966A"
    link_economybookings = f"https://economybookings.tpo.li/sAJAcIdv"

    # Catalogo de vehiculos predefinidos con precios escalados
    coches = [
        {
            "nombre": "Economico",
            "tipo": "Economico",
            "transmision": "Manual",
            "pasajeros": 4,
            "maletas": 2,
            "precio_total": round(precio_total * 0.8, 2),
            "moneda": "USD",
            "proveedor": "Local",
            "link_reserva": link_base,
            "link_localrent": link_localrent,
            "link_economybookings": link_economybookings,
            "foto_url": "",
        },
        {
            "nombre": "Compacto",
            "tipo": "Compacto",
            "transmision": "Automatica",
            "pasajeros": 5,
            "maletas": 3,
            "precio_total": precio_total,
            "moneda": "USD",
            "proveedor": "Local",
            "link_reserva": link_base,
            "link_localrent": link_localrent,
            "link_economybookings": link_economybookings,
            "foto_url": "",
        },
        {
            "nombre": "SUV",
            "tipo": "SUV",
            "transmision": "Automatica",
            "pasajeros": 5,
            "maletas": 4,
            "precio_total": round(precio_total * 1.5, 2),
            "moneda": "USD",
            "proveedor": "Local",
            "link_reserva": link_base,
            "link_localrent": link_localrent,
            "link_economybookings": link_economybookings,
            "foto_url": "",
        },
        {
            "nombre": "Familiar",
            "tipo": "Familiar",
            "transmision": "Automatica",
            "pasajeros": 7,
            "maletas": 5,
            "precio_total": round(precio_total * 2.0, 2),
            "moneda": "USD",
            "proveedor": "Local",
            "link_reserva": link_base,
            "link_localrent": link_localrent,
            "link_economybookings": link_economybookings,
            "foto_url": "",
        },
    ]
    return {
        "ciudad": iata,
        "coches": coches,
        "aviso": "Precios estimados basados en tarifas promedio de la zona. Reserva directa via Localrent o EconomyBookings.",
    }


async def buscar_coches(
    iata: str,
    pickup_date: str | None = None,
    dropoff_date: str | None = None,
    pickup_time: str = "10:00",
    dropoff_time: str = "10:00",
    driver_age: int = 30,
    currency: str = "USD",
) -> dict:
    """
    Busca opciones de alquiler de coches en una ciudad.

    Args:
        iata: Código IATA de la ciudad de recogida/devolución
        pickup_date: Fecha de recogida (YYYY-MM-DD)
        dropoff_date: Fecha de devolución (YYYY-MM-DD)
        pickup_time: Hora de recogida (HH:MM)
        dropoff_time: Hora de devolución (HH:MM)
        driver_age: Edad del conductor principal
        currency: Moneda del precio (USD, EUR, etc.)

    Returns:
        Dict con 'ciudad', 'coches' (lista) y 'aviso' (str|None)
    """
    # Obtener coordenadas para la búsqueda
    lat, lng = _get_coords(iata)

    # Parámetros para la API de RapidAPI/Booking.com
    params: dict = {
        "pick_up_latitude": str(lat),
        "pick_up_longitude": str(lng),
        "drop_off_latitude": str(lat),
        "drop_off_longitude": str(lng),
        "pick_up_time": pickup_time,
        "drop_off_time": dropoff_time,
        "driver_age": str(driver_age),
        "currency_code": currency,
        "location": iata,
    }
    if pickup_date:
        params["pick_up_date"] = pickup_date
    if dropoff_date:
        params["drop_off_date"] = dropoff_date

    keys = settings.rapidapi_keys
    if not keys:
        return _generar_fallback(iata, pickup_date, dropoff_date)

    try:
        # Llamada a la API de Booking.com via RapidAPI
        # (soporte multi-key con rotación en 401/403/429)
        res = None
        for i, key in enumerate(keys):
            res = await http_client.get(
                "https://booking-com15.p.rapidapi.com/api/v1/cars/searchCarRentals",
                params=params,
                headers={
                    "x-rapidapi-key": key,
                    "x-rapidapi-host": settings.rapidapi_host,
                    "Content-Type": "application/json",
                },
            )
            if res.status_code in (401, 403, 429) and i < len(keys) - 1:
                logger.warning(f"Key RapidAPI #{i + 1} respondió HTTP {res.status_code}, rotando a la siguiente")
                continue
            break
        res.raise_for_status()
        data = res.json()

        # Si la API devuelve error, usar fallback
        if isinstance(data, dict) and data.get("status") is False:
            logger.warning(f"RapidAPI coches devolvió status=false para '{iata}': {data.get('message', '')}")
            return _generar_fallback(iata, pickup_date, dropoff_date)

        # Extraer resultados de diferentes formatos posibles
        coches = []
        results = []
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = data.get("data", data.get("results", []))

        # Si no hay resultados, usar fallback
        if not results:
            return _generar_fallback(iata, pickup_date, dropoff_date)

        # Transformar datos de la API al formato unificado
        for c in results:
            precio = float(c.get("price", c.get("total_price", 0)))
            coches.append({
                "nombre": c.get("name", c.get("vehicle_name", "Coche")),
                "tipo": c.get("type", c.get("vehicle_type", "")),
                "transmision": c.get("transmission", c.get("transmission_type", "")),
                "pasajeros": c.get("seats", c.get("passengers", 4)),
                "maletas": c.get("bags", c.get("suitcases", 2)),
                "precio_total": precio,
                "moneda": c.get("currency", currency),
                "proveedor": c.get("provider", c.get("supplier", {}).get("name", "")),
                "link_reserva": c.get("deep_link", c.get("link", "")),
                "foto_url": c.get("image", c.get("photo_url", "")),
            })

        return {
            "ciudad": iata,
            "coches": sorted(coches, key=lambda x: x["precio_total"]),  # Ordenar por precio
            "aviso": None,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP coches: {e.response.status_code} - {e.response.text}")
        return _generar_fallback(iata, pickup_date, dropoff_date)
    except httpx.RequestError as e:
        logger.error(f"Error de conexión coches: {e}")
        return _generar_fallback(iata, pickup_date, dropoff_date)
    except Exception as e:
        logger.error(f"Error inesperado en buscar_coches: {e}")
        return _generar_fallback(iata, pickup_date, dropoff_date)