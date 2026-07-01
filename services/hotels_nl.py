# services/hotels_nl.py
# Integracion con Hotels.nl API para busqueda de hoteles reales
# Docs: https://hotels.nl/api/
# Free tier: 200 requests/day, 5 requests/min

import logging
from typing import Optional

from core.config import settings
from core.http import http_client, request_with_retry

logger = logging.getLogger(__name__)

API_BASE = "https://hotels.nl/api"


async def buscar_hoteles(
    location: str,
    checkin: str,
    checkout: str,
    currency: str = "USD",
    persons: int = 2,
    language: str = "es",
    residency: str = "co",
) -> Optional[list[dict]]:
    """
    Busca hoteles reales via Hotels.nl API.

    Args:
        location: Ciudad o direccion
        checkin: YYYY-MM-DD
        checkout: YYYY-MM-DD
        currency: USD, EUR, etc
        persons: Numero de adultos
        language: es, en, nl, etc
        residency: Codigo pais del huesped

    Returns:
        Lista de hoteles normalizados, o None si falla
    """
    api_key = settings.hotelsnl_api_key
    if not api_key:
        logger.debug("Hotels.nl API key no configurada")
        return None

    try:
        res = await request_with_retry(
            "POST",
            f"{API_BASE}/search.php",
            provider="hotelsnl",
            json={
                "apikey": api_key,
                "location": location,
                "checkin": checkin,
                "checkout": checkout,
                "currency": currency,
                "persons": persons,
                "language": language,
                "residency": residency,
                "include_amenities": True,
                "include_description": True,
                "kind": ["Hotel"],
            },
        )

        if res.status_code == 403:
            logger.warning("Hotels.nl API: key invalida")
            return None
        if res.status_code == 429:
            logger.warning("Hotels.nl API: rate limit excedido")
            return None

        res.raise_for_status()
        data = res.json()

        hotels_raw = data.get("hotels", [])
        if not hotels_raw:
            logger.debug(f"Hotels.nl: sin resultados para '{location}'")
            return []

        search_info = data.get("search", {})
        hotels = []
        for h in hotels_raw:
            rate = h.get("rate", {})
            pricing = rate.get("pricing", {})
            room = rate.get("room", {})

            amenities_raw = h.get("amenities", "")
            amenities = [a.strip() for a in amenities_raw.split(",") if a.strip()]

            total_price_str = pricing.get("total_price", "0")
            try:
                total_price = float(total_price_str)
            except (ValueError, TypeError):
                total_price = 0.0

            nightly = total_price / max(search_info.get("nights", 1), 1)

            image_url = h.get("image", "")

            stars = h.get("star_rating", 0) or 0

            hotels.append({
                "id_hotelsnl": h.get("id"),
                "nombre": h.get("name", ""),
                "estrellas": stars,
                "rating": _stars_to_rating(stars),
                "reviewScoreWord": _rating_word(stars),
                "reviewCount": _stars_to_reviews(stars),
                "direccion": h.get("address", ""),
                "ciudad": h.get("city", location),
                "pais": h.get("country_code", ""),
                "tipo_propiedad": h.get("kind", ""),
                "foto_url": image_url,
                "fotos_urls": [image_url] if image_url else [],
                "precio_noche": round(nightly, 2),
                "precio_total": round(total_price, 2),
                "noches": search_info.get("nights", 1),
                "adultos": persons,
                "moneda": pricing.get("currency", currency),
                "hotelsnl_hash": rate.get("hotelsnl_hash", ""),
                "descripcion": h.get("short_description", ""),
                "amenities": amenities,
                "por_que": f"Hotel real en {h.get('city', location)} con precio desde Hotels.nl.",
                "tipo": "real",
            })

        return hotels

    except Exception as e:
        logger.warning(f"Hotels.nl API error para '{location}': {e}")
        return None


async def obtener_detalle(
    hotel_id: int | str,
    checkin: str,
    checkout: str,
    persons: int = 2,
    currency: str = "USD",
    language: str = "es",
    residency: str = "co",
) -> Optional[dict]:
    """
    Obtiene el detalle completo de un hotel via Hotels.nl /api/hotel.php:
    galeria de imagenes + todas las habitaciones/tarifas disponibles.

    Returns:
        Dict normalizado {nombre, descripcion, fotos_urls, habitaciones}, o None si falla.
    """
    api_key = settings.hotelsnl_api_key
    if not api_key:
        return None

    try:
        hid = int(hotel_id)
    except (ValueError, TypeError):
        logger.warning(f"Hotels.nl detalle: id invalido '{hotel_id}'")
        return None

    try:
        res = await request_with_retry(
            "POST",
            f"{API_BASE}/hotel.php",
            provider="hotelsnl",
            json={
                "apikey": api_key,
                "id": hid,
                "checkin": checkin,
                "checkout": checkout,
                "persons": persons,
                "currency": currency,
                "language": language,
                "residency": residency,
            },
        )

        if res.status_code in (403, 429):
            logger.warning(f"Hotels.nl hotel.php status {res.status_code} para id {hid}")
            return None

        res.raise_for_status()
        data = res.json()

        # Galeria de imagenes (array de {url, category})
        fotos_urls = [img.get("url") for img in data.get("images", []) if img.get("url")]

        # Descripcion (array de {title, text})
        descripciones = data.get("descriptions", [])
        descripcion = descripciones[0].get("text", "") if descripciones else ""

        # Habitaciones: por cada room, su tarifa mas barata
        habitaciones = []
        for room in data.get("rooms", []):
            rates = room.get("rates", [])
            if not rates:
                continue
            mejor = min(rates, key=lambda r: _to_float(r.get("pricing", {}).get("total_price")))
            pricing = mejor.get("pricing", {})
            total = _to_float(pricing.get("total_price"))
            noche = _to_float(pricing.get("price_per_night")) or _to_float(pricing.get("average_per_night"))
            habitaciones.append({
                "nombre": room.get("room_name", "") or room.get("room_type", "Habitación"),
                "capacidad": room.get("capacity"),
                "cama": room.get("bedding", ""),
                "comida": mejor.get("meal", ""),
                "reembolsable": mejor.get("refundable"),
                "precio_total": round(total, 2),
                "precio_noche": round(noche, 2) if noche else None,
                "moneda": pricing.get("currency", currency),
                "hotelsnl_hash": mejor.get("hotelsnl_hash", ""),
            })

        # Ordenar habitaciones por precio ascendente
        habitaciones.sort(key=lambda h: h.get("precio_total") or 0)

        return {
            "nombre": data.get("name", ""),
            "descripcion": descripcion,
            "fotos_urls": fotos_urls,
            "habitaciones": habitaciones,
        }

    except Exception as e:
        logger.warning(f"Hotels.nl hotel.php error para id {hotel_id}: {e}")
        return None


def _to_float(value) -> float:
    """Convierte un valor a float de forma segura (0.0 si falla)."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _stars_to_rating(stars: int) -> float:
    """Convierte estrellas a rating aproximado."""
    mapping = {0: 0, 1: 5.5, 2: 6.0, 3: 7.0, 4: 8.0, 5: 9.0}
    return mapping.get(stars, 0)


def _rating_word(stars: int) -> str:
    """Palabra descriptiva segun estrellas."""
    mapping = {0: "", 1: "Aceptable", 2: "Bien", 3: "Bien", 4: "Muy bien", 5: "Excelente"}
    return mapping.get(stars, "")


def _stars_to_reviews(stars: int) -> int:
    """Numero de reviews estimado segun estrellas."""
    mapping = {0: 0, 1: 30, 2: 80, 3: 150, 4: 300, 5: 500}
    return mapping.get(stars, 0)
