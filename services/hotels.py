# services/hotels.py
# Servicio de búsqueda de hoteles con fallback doble (RapidAPI → Travelpayouts → estimado)
# Utiliza Booking.com como fuente principal de datos

import json
import logging
import re
from datetime import date
from core.config import settings
from core.http import http_client
from core.database_cache import cache_get, cache_get_stale, cache_set

logger = logging.getLogger(__name__)

# Headers fijos para todas las llamadas a RapidAPI
def _rapid_headers() -> dict:
    """Devuelve headers actualizados para RapidAPI (evita valores stale del import)."""
    return {
        "x-rapidapi-key": settings.rapidapi_key,
        "x-rapidapi-host": settings.rapidapi_host,
        "Content-Type": "application/json",
    }

# Cache TTL en segundos (24 horas para hoteles)
_CACHE_TTL = 24 * 3600


def _cache_key(ciudad: str, checkin: str, checkout: str, adultos: int, estrellas_min: int, estrellas_max: int) -> str:
    """Genera key única para cache de hoteles."""
    return f"hotels:{ciudad}:{checkin}:{checkout}:{adultos}:{estrellas_min}:{estrellas_max}"


def _estimar_hoteles(ciudad: str, checkin: str, checkout: str, adultos: int, iata: str = "") -> dict:
    """
    Genera hoteles estimados usando precios de referencia cuando la API no está disponible.
    Sin llamadas a APIs externas.

    Args:
        ciudad: Nombre de la ciudad
        checkin: Fecha de entrada
        checkout: Fecha de salida
        adultos: Número de adultos
        iata: Código IATA opcional para precio de referencia

    Returns:
        Dict con hoteles estimados
    """
    noches = _calcular_noches(checkin, checkout)
    precio_noche = _precio_referencia(iata) if iata else _precio_referencia(ciudad)
    precio_total = round(precio_noche * noches, 2)

    hoteles_estimados = []
    nombres = [
        f"Hotel Céntrico en {ciudad}",
        f"Hotel Boutique en {ciudad}",
        f"Hotel Ejecutivo en {ciudad}",
    ]
    for i, nombre in enumerate(nombres):
        hoteles_estimados.append({
            "nombre": nombre,
            "estrellas": 3 + i,
            "rating": round(7.0 + i * 0.5, 1),
            "reviewScoreWord": ["Bien", "Muy bien", "Excelente"][i],
            "reviewCount": 50 + i * 25,
            "foto_url": f"https://placehold.co/600x400?text={nombre.replace(' ', '+')}",
            "fotos_urls": [],
            "precio_noche": round(precio_noche * (0.9 + i * 0.1), 2),
            "precio_total": round(precio_noche * noches * (0.9 + i * 0.1), 2),
            "noches": noches,
            "adultos": adultos,
            "moneda": "USD",
            "link_reserva": f"https://www.booking.com/searchresults.html?ss={ciudad.replace(' ', '+')}&checkin={checkin}&checkout={checkout}&group_adults={adultos}&selected_currency=USD",
            "por_que": "Precio estimado basado en tarifas promedio de la zona.",
            "tipo": "estimado",
            "amenities": [],
        })

    return {
        "aviso": "Mostrando hoteles estimados basados en tarifas de referencia. Los precios reales pueden variar.",
        "ciudad": ciudad,
        "hoteles": hoteles_estimados,
        "precision": "estimada",
    }


# Precios de referencia por noche en USD segun codigo IATA de la ciudad
# Usados como fallback cuando la API no responde
# Fuente unica de verdad: cualquier cambio aqui se refleja en todo el sistema
PRECIO_REFERENCIA_HOTEL: dict[str, float] = {
    # Colombia
    "BOG": 45,  "MDE": 50,  "CLO": 40,  "CTG": 70,  "BAQ": 45,
    # Mexico y Caribe
    "MIA": 120, "MCO": 100, "CUN": 85,  "MEX": 70,  "GDL": 60,
    "LIM": 55,  "GYE": 45,  "UIO": 50,  "SDQ": 75,  "HAV": 90,
    "PTY": 80,  "SJO": 75,  "SCL": 80,  "EZE": 65,  "GRU": 70,
    # Estados Unidos
    "JFK": 200, "LAX": 170, "ORD": 140, "LAS": 90,  "SFO": 190,
    "BOS": 160, "DCA": 150, "ATL": 110,
    # Europa
    "MAD": 90,  "BCN": 100, "LHR": 180, "CDG": 160, "FCO": 130,
    "AMS": 150, "FRA": 130, "LIS": 95,  "VIE": 110, "ZRH": 200,
    "_default": 80,
}


def _calcular_noches(checkin: str, checkout: str) -> int:
    """
    Calcula el número de noches entre check-in y check-out.
    Asegura mínimo 1 noche.

    Args:
        checkin: Fecha de entrada (YYYY-MM-DD)
        checkout: Fecha de salida (YYYY-MM-DD)

    Returns:
        Número de noches (mínimo 1)
    """
    noches = (date.fromisoformat(checkout) - date.fromisoformat(checkin)).days or 1
    return max(noches, 1)


def _precio_referencia(ciudad: str) -> float:
    """Obtiene el precio de referencia por noche para una ciudad."""
    return PRECIO_REFERENCIA_HOTEL.get(ciudad.upper(), PRECIO_REFERENCIA_HOTEL["_default"])


def _slug_hotel(nombre: str) -> str:
    """Convierte nombre de hotel a slug URL-friendly."""
    return re.sub(r'[^a-z0-9]+', '-', nombre.lower()).strip('-')


async def _buscar_rapidapi(ciudad: str, checkin: str, checkout: str, adultos: int) -> dict | None:
    """
    Busca hoteles reales usando la API de Booking.com via RapidAPI.

    Proceso en 2 pasos:
      1. Buscar destination_id de la ciudad
      2. Buscar hoteles disponibles en esa ciudad

    Args:
        ciudad: Nombre de la ciudad a buscar
        checkin: Fecha de entrada (YYYY-MM-DD)
        checkout: Fecha de salida (YYYY-MM-DD)
        adultos: Número de adultos

    Returns:
        Dict con hoteles encontrados o None si falla la API
    """
    try:
        # Paso 1: Obtener destination_id para la ciudad
        r1 = await http_client.get(
            "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination",
            params={"query": ciudad},
            headers=_rapid_headers(),
        )
        r1.raise_for_status()
        data1 = r1.json()

        if not data1.get("status"):
            return None

        dests = data1.get("data", [])
        if not dests:
            return None

        # Tomar el primer resultado (más relevante)
        dest_id = dests[0].get("dest_id")
        nombre_ciudad = dests[0].get("name") or dests[0].get("city_name", ciudad)
        country_code = dests[0].get("cc1", "")

        # Paso 2: Buscar hoteles en esa ciudad
        r2 = await http_client.get(
            "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels",
            params={
                "dest_id": dest_id,
                "search_type": "city",
                "arrival_date": checkin,
                "departure_date": checkout,
                "adults": adultos,
                "currency_code": "USD",
            },
            headers=_rapid_headers(),
        )
        r2.raise_for_status()
        data2 = r2.json()

        if not data2.get("status"):
            return None

        # Extraer lista de hoteles de la respuesta
        raw = data2.get("data", {})
        hoteles_raw = raw.get("hotels", [])
        if not isinstance(hoteles_raw, list):
            hoteles_raw = []

        noches = _calcular_noches(checkin, checkout)
        hoteles = []

        for i, h in enumerate(hoteles_raw):
            if not isinstance(h, dict):
                continue
            prop = h.get("property", h)

            # Log de debug para el primer hotel (para debugging)
            if i == 0 and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Hotel raw: {json.dumps(h, default=str)[:2000]}")

            # Extraer precio de diferentes fuentes posibles
            pb = prop.get("priceBreakdown", {})
            gross = pb.get("grossPrice", {})
            precio_noche = float(gross.get("value", prop.get("price", 0)))
            if not precio_noche:
                precio_noche = float(prop.get("minPrice", 0))

            precio_total = round(precio_noche * noches, 2)
            hotel_id = prop.get("id", h.get("hotel_id", ""))
            hotel_name = prop.get("name", "Hotel")

            # Extraer fotos del hotel (hasta 5) de diferentes formatos posibles
            fotos_urls = []
            fotos_raw = (
                prop.get("photoUrls")
                or prop.get("photos")
                or prop.get("images")
                or []
            )
            if fotos_raw and isinstance(fotos_raw, list):
                for f in fotos_raw[:5]:
                    if isinstance(f, str) and f.startswith(("http://", "https://")):
                        fotos_urls.append(f)
                    elif isinstance(f, dict):
                        url = f.get("url", f.get("path", ""))
                        if url and url.startswith(("http://", "https://")):
                            fotos_urls.append(url)

            foto_url = fotos_urls[0] if fotos_urls else ""
            # Fallback para foto si no se encontró
            if not foto_url:
                fotos_urls = []
                foto_url = (
                    prop.get("image")
                    or prop.get("photo_url")
                    or prop.get("mainPhoto")
                    or prop.get("heroImage")
                    or ""
                )
            # Último fallback: placeholder con nombre del hotel
            if not foto_url:
                foto_url = f"https://placehold.co/600x400?text={hotel_name.replace(' ', '+')}"
                fotos_urls = [foto_url]

            # Extraer amenities de la respuesta (si existen)
            amenities = []
            raw_amenities = (
                prop.get("amenities")
                or prop.get("facilities")
                or prop.get("hotelFacilities")
                or []
            )
            if raw_amenities and isinstance(raw_amenities, list):
                for a in raw_amenities:
                    if isinstance(a, str):
                        amenities.append(a)
                    elif isinstance(a, dict):
                        amenities.append(a.get("name") or a.get("label") or "")

            # Generar link de reserva en Booking.com
            if country_code and hotel_id:
                link = (
                    f"https://www.booking.com/hotel/{country_code}/{hotel_id}.html"
                    f"?checkin={checkin}&checkout={checkout}"
                    f"&group_adults={adultos}&selected_currency=USD"
                )
            else:
                link = (
                    f"https://www.booking.com/searchresults.html?"
                    f"dest_id={dest_id}&dest_type=city&checkin={checkin}"
                    f"&checkout={checkout}&group_adults={adultos}"
                    f"&selected_currency=USD"
                )
                if hotel_id:
                    link += f"&hotel_id={hotel_id}"

            logger.debug(f"Link generado: {link}")

            # Agregar hotel al resultado
            hoteles.append({
                "nombre": hotel_name,
                "estrellas": prop.get("qualityClass", prop.get("accuratePropertyClass", 0)),
                "rating": prop.get("reviewScore", 0),
                "reviewScoreWord": prop.get("reviewScoreWord", ""),
                "reviewCount": prop.get("reviewCount", 0),
                "foto_url": foto_url,
                "fotos_urls": fotos_urls,
                "precio_noche": precio_noche,
                "precio_total": precio_total,
                "noches": noches,
                "adultos": adultos,
                "moneda": prop.get("currency", "USD"),
                "link_reserva": link,
                "por_que": "",  # Campo vacío para hoteles reales
                "tipo": "real",  # Marca como hotel real (vs estimado)
                "amenities": amenities,
            })

        return {
            "aviso": None,
            "ciudad": nombre_ciudad or ciudad,
            "hoteles": sorted(hoteles, key=lambda x: x["precio_total"]),
            "precision": "exacta",
        }
    except Exception as e:
        logger.warning(f"RapidAPI fallo para '{ciudad}': {e}")
        return {"error": f"Error al consultar hoteles: {e}", "hoteles": []}


async def _buscar_travelpayouts(ciudad: str, checkin: str, checkout: str, adultos: int) -> dict | None:
    """
    Busca hoteles usando Travelpayouts como fallback cuando RapidAPI falla.
    Devuelve un único hotel estimado con precio de referencia.

    Args:
        ciudad: Nombre de la ciudad
        checkin: Fecha de entrada
        checkout: Fecha de salida
        adultos: Número de adultos

    Returns:
        Dict con hotel estimado o None si falla
    """
    try:
        # Buscar código IATA de la ciudad
        res = await http_client.get(
            "https://autocomplete.travelpayouts.com/places2",
            params={"term": ciudad, "locale": "es", "types": "city"},
        )
        res.raise_for_status()
        data = res.json()

        if not data:
            return None

        city = data[0]
        nombre = city.get("name", ciudad)
        codigo = city.get("code", "")
        pais = city.get("country_name", "")

        noches = _calcular_noches(checkin, checkout)
        precio_noche = _precio_referencia(codigo)
        precio_total = round(precio_noche * noches, 2)

        # Generar link de búsqueda en Booking.com
        link = (
            f"https://www.booking.com/searchresults.html?"
            f"ss={nombre.replace(' ', '+')}&checkin={checkin}"
            f"&checkout={checkout}&group_adults={adultos}"
            f"&selected_currency=USD"
        )

        return {
            "aviso": None,
            "ciudad": f"{nombre}, {pais}".strip(", "),
            "precision": "estimada",
            "hoteles": [{
                "nombre": f"Hoteles en {nombre}",
                "estrellas": 3,
                "rating": 0,
                "foto_url": "",
                "precio_noche": precio_noche,
                "precio_total": precio_total,
                "noches": noches,
                "adultos": adultos,
                "moneda": "USD",
                "link_reserva": link,
                "por_que": "Precio estimado basado en tarifas promedio de la zona.",
                "tipo": "estimado",  # Marca como hotel estimado
            }],
        }
    except Exception as e:
        logger.warning(f"Travelpayouts fallo para '{ciudad}': {e}")
        return {"error": f"Error en fallback de hoteles: {e}", "hoteles": []}


async def buscar_hoteles(
    ciudad: str,
    checkin: str,
    checkout: str,
    adultos: int = 2,
    estrellas_min: int = 1,
    estrellas_max: int = 5,
    q: str = "",
) -> dict:
    """
    Busca hoteles con estrategia de 4 niveles:
      1. Cache persistente SQLite
      2. RapidAPI (Booking.com) → datos reales
      3. Travelpayouts → hotel estimado con precio de referencia
      4. Datos estimados locales

    Args:
        ciudad: Nombre de la ciudad
        checkin: Fecha de entrada (YYYY-MM-DD)
        checkout: Fecha de salida (YYYY-MM-DD)
        adultos: Número de adultos (default: 2)
        estrellas_min: Filtrar por estrellas mínimas (default: 1)
        estrellas_max: Filtrar por estrellas máximas (default: 5)
        q: Filtrar hoteles por nombre (case-insensitive, opcional)

    Returns:
        Dict con 'aviso', 'ciudad', 'hoteles' (lista)
    """
    cache_key = _cache_key(ciudad, checkin, checkout, adultos, estrellas_min, estrellas_max)

    # Nivel 0: Cache persistente
    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit para hoteles: {cache_key}")
        hoteles = cached["hoteles"]
        if q:
            q_lower = q.lower()
            hoteles = [h for h in hoteles if q_lower in h.get("nombre", "").lower()]
        return {
            "aviso": cached.get("aviso"),
            "ciudad": cached.get("ciudad", ciudad),
            "hoteles": hoteles,
        }

    # Nivel 1: RapidAPI (datos reales)
    resultado = await _buscar_rapidapi(ciudad, checkin, checkout, adultos)
    if resultado and resultado.get("hoteles") and not resultado.get("error"):
        hoteles = resultado["hoteles"]
        hoteles_filtrados = [h for h in hoteles if estrellas_min <= (h.get("estrellas") or 0) <= estrellas_max]
        if not hoteles_filtrados:
            cache_set(cache_key, resultado, provider="rapidapi", ttl_seconds=_CACHE_TTL)
            return {
                "aviso": f"No se encontraron hoteles de {estrellas_min}-{estrellas_max} estrellas en {ciudad}. Intenta con otro nivel de calidad.",
                "ciudad": resultado.get("ciudad", ciudad),
                "hoteles": [],
            }
        resultado["hoteles"] = hoteles_filtrados
        cache_set(cache_key, resultado, provider="rapidapi", ttl_seconds=_CACHE_TTL)
        if q:
            q_lower = q.lower()
            hoteles_filtrados = [h for h in hoteles_filtrados if q_lower in h.get("nombre", "").lower()]
        return {
            "aviso": resultado.get("aviso"),
            "ciudad": resultado.get("ciudad", ciudad),
            "hoteles": hoteles_filtrados,
        }

    # Nivel 2: Travelpayouts (hotel estimado con precio de referencia)
    logger.info(f"Fallback a Travelpayouts para '{ciudad}'")
    resultado = await _buscar_travelpayouts(ciudad, checkin, checkout, adultos)
    if resultado and resultado.get("hoteles"):
        resultado["precision"] = "estimada"
        cache_set(cache_key, resultado, provider="travelpayouts", ttl_seconds=_CACHE_TTL)
        return resultado

    # Intentar cache stale si API falló
    stale = cache_get_stale(cache_key)
    if stale is not None:
        stale["aviso"] = "Mostrando datos de cache previo. Los precios pueden no estar actualizados."
        stale["precision"] = "stale"
        return stale

    # Nivel 3: Datos estimados locales (0 llamadas API)
    logger.warning(f"API de hoteles no disponible para '{ciudad}', usando datos estimados")
    iata = resultado.get("codigo_iata", "") if isinstance(resultado, dict) else ""
    estimados = _estimar_hoteles(ciudad, checkin, checkout, adultos, iata=iata)
    estimados["precision"] = "estimada"
    cache_set(cache_key, estimados, provider="reference", ttl_seconds=_CACHE_TTL)
    return estimados