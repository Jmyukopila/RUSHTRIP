# services/hotels.py
# Servicio de busqueda de hoteles con fallback multiple
# Hotels.nl API (datos reales) → Travelpayouts → fallback estimados

import logging
import re
from datetime import date
from urllib.parse import quote
from core.config import settings
from core.http import request_with_retry
from core.database_cache import cache_get, cache_get_stale, cache_set
from core.cache import TTLCache
from services.airports import buscar_aeropuerto
from services.hotels_nl import buscar_hoteles as buscar_hoteles_nl
from services.hotels_nl import obtener_detalle as obtener_detalle_nl

logger = logging.getLogger(__name__)

# Cache TTL en segundos (24 horas para hoteles, 1 hora para fotos)
_CACHE_TTL = 24 * 3600
_PEXELS_CACHE = TTLCache(ttl_seconds=3600)


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
            "link_reserva": _link_reserva_tp(nombre, ciudad, checkin, checkout, adultos),
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


def _link_reserva_tp(nombre: str, ciudad: str, checkin: str, checkout: str, adultos: int) -> str:
    """
    Genera el link de reserva del hotel concreto.

    Construye un deep-link a Booking.com (nombre exacto + ciudad + fechas +
    ocupacion) que aterriza en/junto a la ficha del hotel con las fechas ya
    cargadas. Si hay un prefijo de afiliado configurado
    (settings.travelpayouts_hotel_link), lo envuelve (+ '&u=<destino>') para
    generar comision. En desarrollo el prefijo esta vacio => Booking.com directo,
    sin afiliacion (no requiere aprobacion ni cuenta de programa).
    """
    consulta = f"{nombre} {ciudad}".strip()
    destino = (
        "https://www.booking.com/searchresults.html?"
        f"ss={quote(consulta)}&checkin={checkin}&checkout={checkout}"
        f"&group_adults={adultos}&selected_currency=USD"
    )
    prefijo = settings.travelpayouts_hotel_link.strip()
    if prefijo:
        sep = "&" if "?" in prefijo else "?"
        return f"{prefijo}{sep}u={quote(destino, safe='')}"
    return destino


def _slug_hotel(nombre: str) -> str:
    """Convierte nombre de hotel a slug URL-friendly."""
    return re.sub(r'[^a-z0-9]+', '-', nombre.lower()).strip('-')


async def _enriquecer_con_fotos(ciudad: str, hoteles: list) -> list:
    """Obtiene fotos reales del destino via Pexels API y las asigna a los hoteles."""
    if not settings.pexels_api_key:
        return hoteles
    cache_key = f"pexels_{ciudad.lower().replace(' ', '_')}"
    fotos = _PEXELS_CACHE.get(cache_key)
    if fotos is None:
        try:
            res = await request_with_retry(
                "GET",
                "https://api.pexels.com/v1/search",
                provider="pexels",
                max_retries=1,
                params={"query": f"{ciudad} hotel", "per_page": 4, "orientation": "landscape"},
                headers={"Authorization": settings.pexels_api_key},
            )
            data = res.json()
            fotos = [p["src"]["medium"] for p in data.get("photos", [])]
            _PEXELS_CACHE.set(cache_key, fotos)
        except Exception as e:
            logger.warning(f"Pexels API fallo para '{ciudad}': {e}")
            fotos = []
    for h in hoteles:
        # Preservar la imagen real propia del hotel (Hotels.nl); solo los hoteles
        # estimados reciben las fotos de stock de la ciudad de Pexels.
        if h.get("tipo") == "real" and h.get("foto_url"):
            continue
        h["foto_url"] = fotos[0] if fotos else f"https://placehold.co/600x400?text={quote(h['nombre'])}"
        h["fotos_urls"] = fotos if fotos else []
    return hoteles


async def _buscar_ciudad(ciudad: str) -> dict | None:
    """
    Obtiene info de una ciudad reutilizando el autocomplete de aeropuertos
    (mismo endpoint de Travelpayouts, con cache en memoria + SQLite compartido).
    """
    try:
        resultados = await buscar_aeropuerto(ciudad)
        if not resultados:
            return None
        city = resultados[0]
        return {
            "nombre": city.get("nombre") or ciudad,
            "codigo": city.get("codigo") or "",
            "pais": city.get("pais") or "",
            "pais_codigo": (city.get("pais_codigo") or "").upper(),
        }
    except Exception as e:
        logger.warning(f"Travelpayouts autocomplete fallo para '{ciudad}': {e}")
        return None


def _generar_hoteles_afiliados(
    ciudad: str,
    checkin: str,
    checkout: str,
    adultos: int,
    noches: int,
    precio_noche: float,
) -> list[dict]:
    """Genera hoteles con precios de referencia + links de afiliado Booking/KKday/Klook."""
    categorias = [
        ("Hotel Céntrico", 3, 7.5, "Bien", 50, 0.9),
        ("Hotel Boutique", 4, 8.0, "Muy bien", 100, 1.0),
        ("Hotel Ejecutivo", 4, 8.5, "Excelente", 150, 1.15),
        ("Resort Premium", 5, 9.0, "Excelente", 200, 1.3),
    ]

    hoteles = []
    for nombre, estrellas, rating, score_word, reviews, factor in categorias:
        full_name = f"{nombre} en {ciudad}"
        pn = round(precio_noche * factor, 2)
        pt = round(pn * noches, 2)
        hoteles.append({
            "nombre": full_name,
            "estrellas": estrellas,
            "rating": rating,
            "reviewScoreWord": score_word,
            "reviewCount": reviews,
            "foto_url": f"https://placehold.co/600x400?text={full_name.replace(' ', '+')}",
            "fotos_urls": [],
            "precio_noche": pn,
            "precio_total": pt,
            "noches": noches,
            "adultos": adultos,
            "moneda": "USD",
            "link_reserva": _link_reserva_tp(full_name, ciudad, checkin, checkout, adultos),
            "link_kkday": f"https://kkday.tpo.li/zHk5IFqZ?dest={ciudad.lower().replace(' ', '-')}",
            "link_klook": f"https://klook.tpo.li/GBfSCVf0?dest={ciudad.lower().replace(' ', '-')}",
            "por_que": "Precio de referencia basado en tarifas promedio de la zona.",
            "tipo": "estimado",
            "amenities": [],
        })
    return hoteles


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
    Busca hoteles con estrategia de niveles:
      1. Cache persistente SQLite
      2. Travelpayouts + precios de referencia + links afiliados (KKday/Klook/Booking)
      3. Datos estimados locales

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
        hoteles = await _enriquecer_con_fotos(cached.get("ciudad", ciudad), hoteles)
        if q:
            q_lower = q.lower()
            hoteles = [h for h in hoteles if q_lower in h.get("nombre", "").lower()]
        return {
            "aviso": cached.get("aviso"),
            "ciudad": cached.get("ciudad", ciudad),
            "hoteles": hoteles,
            "precision": cached.get("precision", "estimada"),
        }

    # Resolver la ciudad primero (cacheado): da el nombre canónico para el
    # geocoder de Hotels.nl y el país esperado para validar sus resultados.
    city_info = await _buscar_ciudad(ciudad)
    nombre_ciudad = city_info["nombre"] if city_info else ciudad
    pais_esperado = city_info["pais_codigo"] if city_info else ""
    hoteles = None

    # Nivel 1: Hotels.nl API (datos reales + comisiones)
    if settings.hotelsnl_api_key:
        logger.info(f"Buscando hoteles para '{nombre_ciudad}' via Hotels.nl API")
        hoteles_nl = await buscar_hoteles_nl(
            location=nombre_ciudad,
            checkin=checkin,
            checkout=checkout,
            persons=adultos,
            currency="USD",
        )
        # Validar el país: si Hotels.nl no reconoce la ubicación devuelve
        # hoteles de otro sitio (p.ej. Ámsterdam al buscar 'ZAG')
        if hoteles_nl and pais_esperado:
            coincidentes = [h for h in hoteles_nl if (h.get("pais") or "").upper() == pais_esperado]
            if not coincidentes:
                logger.warning(
                    f"Hotels.nl devolvió hoteles fuera de {pais_esperado} para '{nombre_ciudad}' "
                    f"(ej: {hoteles_nl[0].get('ciudad')}, {hoteles_nl[0].get('pais')}); descartando"
                )
                hoteles_nl = None
            else:
                hoteles_nl = coincidentes
        if hoteles_nl is not None:
            hoteles = hoteles_nl
            if hoteles:
                nombre_ciudad = hoteles[0].get("ciudad", nombre_ciudad)
            # Asignar link de reserva (Travelpayouts -> Booking.com del hotel concreto)
            for h in hoteles:
                h["link_reserva"] = _link_reserva_tp(
                    h.get("nombre", ""), h.get("ciudad", nombre_ciudad), checkin, checkout, adultos
                )

    # Nivel 2: Fallback a Travelpayouts + precios de referencia
    if hoteles is None:
        logger.info(f"Buscando hoteles para '{nombre_ciudad}' via Travelpayouts + afiliados")
        codigo = city_info["codigo"] if city_info else ""
        noches = _calcular_noches(checkin, checkout)
        precio_noche = _precio_referencia(codigo) if codigo else _precio_referencia(ciudad)
        hoteles = _generar_hoteles_afiliados(
            nombre_ciudad, checkin, checkout, adultos, noches, precio_noche
        )

    hoteles = await _enriquecer_con_fotos(nombre_ciudad, hoteles)

    hoteles_filtrados = [h for h in hoteles if estrellas_min <= (h.get("estrellas") or 0) <= estrellas_max]
    if not hoteles_filtrados:
        return {
            "aviso": f"No se encontraron hoteles de {estrellas_min}-{estrellas_max} estrellas en {nombre_ciudad}.",
            "ciudad": nombre_ciudad,
            "hoteles": [],
        }

    if q:
        q_lower = q.lower()
        hoteles_filtrados = [h for h in hoteles_filtrados if q_lower in h.get("nombre", "").lower()]

    es_real = any(h.get("tipo") == "real" for h in hoteles_filtrados)
    resultado = {
        "aviso": "Precios reales de Hotels.nl. Al reservar generas comision." if es_real
                  else "Mostrando precios de referencia. Los precios reales pueden variar.",
        "ciudad": nombre_ciudad,
        "hoteles": hoteles_filtrados,
        "precision": "real" if es_real else "estimada",
    }

    cache_set(cache_key, resultado, provider="hotelsnl" if es_real else "travelpayouts", ttl_seconds=_CACHE_TTL)
    return resultado


async def detalle_hotel(hotel_id: str, checkin: str, checkout: str, adultos: int = 2, ciudad: str = "") -> dict:
    """
    Detalle de un hotel real (Hotels.nl): galeria completa de fotos + habitaciones
    con precio y link de reserva. Pensado para carga on-demand desde el frontend.

    Returns:
        Dict con 'fotos_urls', 'habitaciones' (cada una con 'link_reserva'),
        'descripcion' y 'precision'. Degrada con 'aviso' si no hay datos reales.
    """
    cache_key = f"detalle:{hotel_id}:{checkin}:{checkout}:{adultos}"

    cached = cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit para detalle hotel: {cache_key}")
        return cached

    detalle = await obtener_detalle_nl(
        hotel_id=hotel_id,
        checkin=checkin,
        checkout=checkout,
        persons=adultos,
        currency="USD",
    )

    if detalle is None:
        return {
            "aviso": "No pudimos cargar el detalle de este hotel en este momento.",
            "fotos_urls": [],
            "habitaciones": [],
            "descripcion": "",
            "precision": "estimada",
        }

    nombre = detalle.get("nombre", "")
    # Link de reserva por habitacion (Travelpayouts -> Booking.com del hotel concreto)
    for hab in detalle.get("habitaciones", []):
        hab["link_reserva"] = _link_reserva_tp(nombre, ciudad, checkin, checkout, adultos)

    # Si Hotels.nl no trajo fotos, completar con fotos de la ciudad (Pexels)
    if not detalle.get("fotos_urls"):
        placeholder = [{"nombre": nombre, "tipo": "real", "foto_url": ""}]
        enriquecidos = await _enriquecer_con_fotos(ciudad or nombre, placeholder)
        detalle["fotos_urls"] = enriquecidos[0].get("fotos_urls", [])

    resultado = {
        "nombre": nombre,
        "descripcion": detalle.get("descripcion", ""),
        "fotos_urls": detalle.get("fotos_urls", []),
        "habitaciones": detalle.get("habitaciones", []),
        "precision": "real",
    }

    cache_set(cache_key, resultado, provider="hotelsnl", ttl_seconds=_CACHE_TTL)
    return resultado