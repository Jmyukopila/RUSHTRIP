# services/weather.py
# Servicio de clima del destino via Open-Meteo (gratis, sin API key)
# Estrategia: cache SQLite → pronóstico real (≤16 días) → clima típico histórico → cache stale → None

import logging
from collections import Counter
from datetime import date, datetime, timedelta

from core.database_cache import cache_get, cache_get_stale, cache_set
from core.errors import ExternalAPIError
from core.http import request_with_retry

logger = logging.getLogger(__name__)

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# TTLs de cache
_TTL_FORECAST = 3 * 3600        # 3 horas: el pronóstico cambia varias veces al día
_TTL_TIPICO = 30 * 24 * 3600    # 30 días: el clima típico histórico es estable
_TTL_GEO = 30 * 24 * 3600       # 30 días: las coordenadas de una ciudad no cambian

# El pronóstico de Open-Meteo cubre hasta 16 días (hoy incluido)
_DIAS_FORECAST = 15
# Años anteriores usados para calcular el clima típico
_ANIOS_HISTORICO = 3
# Máximo de días de clima incluidos en la respuesta
_MAX_DIAS = 16

# Mapeo de códigos WMO → (descripción en español, emoji)
WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Despejado", "☀️"),
    1: ("Mayormente despejado", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Niebla", "🌫️"), 48: ("Niebla", "🌫️"),
    51: ("Llovizna", "🌦️"), 53: ("Llovizna", "🌦️"), 55: ("Llovizna", "🌦️"),
    56: ("Llovizna helada", "🌦️"), 57: ("Llovizna helada", "🌦️"),
    61: ("Lluvia ligera", "🌧️"), 63: ("Lluvia", "🌧️"), 65: ("Lluvia fuerte", "🌧️"),
    66: ("Lluvia helada", "🌧️"), 67: ("Lluvia helada", "🌧️"),
    71: ("Nieve ligera", "🌨️"), 73: ("Nieve", "🌨️"), 75: ("Nieve fuerte", "🌨️"),
    77: ("Granos de nieve", "🌨️"),
    80: ("Chubascos", "🌧️"), 81: ("Chubascos", "🌧️"), 82: ("Chubascos fuertes", "🌧️"),
    85: ("Chubascos de nieve", "❄️"), 86: ("Chubascos de nieve", "❄️"),
    95: ("Tormenta", "⛈️"), 96: ("Tormenta con granizo", "⛈️"), 99: ("Tormenta con granizo", "⛈️"),
}


def _describir_codigo(codigo: int) -> tuple[str, str]:
    """Devuelve (descripción, emoji) para un código WMO, con default seguro."""
    return WMO_CODES.get(codigo, ("Variable", "🌥️"))


async def resolver_coords(ciudad: str, iata: str | None = None) -> tuple[float, float] | None:
    """
    Resuelve nombre de ciudad → (lat, lon).
    Cascada: cache → geocoding de Open-Meteo → coordenadas de aeropuerto por IATA.
    """
    cache_key = f"geo:{ciudad.strip().lower()}"
    cached = cache_get(cache_key)
    if cached:
        return (cached[0], cached[1])

    try:
        resp = await request_with_retry(
            "GET", _GEOCODING_URL,
            provider="openmeteo",
            max_retries=1,
            params={"name": ciudad, "count": 1, "language": "es"},
        )
        if resp.status_code == 200:
            results = resp.json().get("results") or []
            if results:
                lat, lon = results[0]["latitude"], results[0]["longitude"]
                cache_set(cache_key, [lat, lon], provider="openmeteo", ttl_seconds=_TTL_GEO)
                return (lat, lon)
    except ExternalAPIError as e:
        logger.warning(f"Geocoding falló para '{ciudad}': {e}")

    # Fallback: coordenadas del aeropuerto de destino si conocemos el IATA
    if iata:
        from services.flights import AEROPUERTO_COORDS
        coords = AEROPUERTO_COORDS.get(iata.upper())
        if coords:
            return coords

    return None


def _parsear_daily(data: dict, tipo: str) -> list[dict]:
    """Convierte los arrays 'daily' de Open-Meteo en lista de días con formato propio."""
    daily = data.get("daily") or {}
    fechas = daily.get("time") or []
    codigos = daily.get("weather_code") or []
    maximas = daily.get("temperature_2m_max") or []
    minimas = daily.get("temperature_2m_min") or []
    prob = daily.get("precipitation_probability_max") or []
    precip = daily.get("precipitation_sum") or []

    dias = []
    for i, fecha in enumerate(fechas):
        codigo = codigos[i] if i < len(codigos) and codigos[i] is not None else None
        temp_max = maximas[i] if i < len(maximas) else None
        temp_min = minimas[i] if i < len(minimas) else None
        if temp_max is None or temp_min is None:
            continue
        descripcion, icono = _describir_codigo(codigo if codigo is not None else -1)
        dia = {
            "fecha": fecha,
            "temp_max": round(temp_max, 1),
            "temp_min": round(temp_min, 1),
            "prob_lluvia": int(prob[i]) if i < len(prob) and prob[i] is not None else None,
            "codigo": codigo,
            "descripcion": descripcion,
            "icono": icono,
            "tipo": tipo,
        }
        if i < len(precip) and precip[i] is not None:
            dia["precipitacion_mm"] = round(precip[i], 1)
        dias.append(dia)
    return dias


async def _obtener_pronostico(lat: float, lon: float, inicio: str, fin: str) -> list[dict]:
    """Pronóstico real día a día (hasta 16 días). Lanza ExternalAPIError si la API falla."""
    cache_key = f"weather:forecast:{round(lat, 2)}:{round(lon, 2)}:{inicio}:{fin}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    resp = await request_with_retry(
        "GET", _FORECAST_URL,
        provider="openmeteo",
        max_retries=1,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "start_date": inicio,
            "end_date": fin,
        },
    )
    if resp.status_code != 200:
        raise ExternalAPIError(
            f"Open-Meteo forecast respondió HTTP {resp.status_code}",
            provider="openmeteo",
            status_code=resp.status_code,
        )

    dias = _parsear_daily(resp.json(), tipo="pronostico")
    if dias:
        cache_set(cache_key, dias, provider="openmeteo", ttl_seconds=_TTL_FORECAST)
    return dias


async def _obtener_tipico(lat: float, lon: float, inicio: str, fin: str) -> list[dict]:
    """
    Clima típico para fechas sin pronóstico posible: promedio de los mismos días
    en los últimos años con datos históricos reales (archive de Open-Meteo).
    """
    cache_key = f"weather:tipico:{round(lat, 2)}:{round(lon, 2)}:{inicio}:{fin}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    fecha_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()
    fecha_fin = datetime.strptime(fin, "%Y-%m-%d").date()

    # Acumula observaciones por día del viaje: indice → lista de (max, min, lluvia_mm, codigo)
    num_dias = (fecha_fin - fecha_inicio).days + 1
    observaciones: list[list[tuple]] = [[] for _ in range(num_dias)]

    # El archive llega hasta hace ~5 días: usar solo años anteriores completos
    anio_base = min(fecha_inicio.year - 1, date.today().year - 1)
    for offset in range(_ANIOS_HISTORICO):
        anio = anio_base - offset
        try:
            hist_inicio = fecha_inicio.replace(year=anio)
            hist_fin = fecha_fin.replace(year=anio + (fecha_fin.year - fecha_inicio.year))
        except ValueError:
            continue  # 29 de febrero en año no bisiesto

        try:
            resp = await request_with_retry(
                "GET", _ARCHIVE_URL,
                provider="openmeteo",
                max_retries=1,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "timezone": "auto",
                    "start_date": hist_inicio.isoformat(),
                    "end_date": hist_fin.isoformat(),
                },
            )
        except ExternalAPIError as e:
            logger.warning(f"Archive de Open-Meteo falló para {anio}: {e}")
            continue
        if resp.status_code != 200:
            continue

        daily = resp.json().get("daily") or {}
        maximas = daily.get("temperature_2m_max") or []
        minimas = daily.get("temperature_2m_min") or []
        lluvias = daily.get("precipitation_sum") or []
        codigos = daily.get("weather_code") or []
        for i in range(min(num_dias, len(maximas))):
            if maximas[i] is None or minimas[i] is None:
                continue
            lluvia = lluvias[i] if i < len(lluvias) and lluvias[i] is not None else 0.0
            codigo = codigos[i] if i < len(codigos) else None
            observaciones[i].append((maximas[i], minimas[i], lluvia, codigo))

    dias = []
    for i in range(num_dias):
        obs = observaciones[i]
        if not obs:
            continue
        codigos_validos = [o[3] for o in obs if o[3] is not None]
        codigo = Counter(codigos_validos).most_common(1)[0][0] if codigos_validos else None
        descripcion, icono = _describir_codigo(codigo if codigo is not None else -1)
        dias.append({
            "fecha": (fecha_inicio + timedelta(days=i)).isoformat(),
            "temp_max": round(sum(o[0] for o in obs) / len(obs), 1),
            "temp_min": round(sum(o[1] for o in obs) / len(obs), 1),
            "prob_lluvia": round(100 * sum(1 for o in obs if o[2] > 1.0) / len(obs)),
            "codigo": codigo,
            "descripcion": descripcion,
            "icono": icono,
            "tipo": "tipico",
        })

    if dias:
        cache_set(cache_key, dias, provider="openmeteo", ttl_seconds=_TTL_TIPICO)
    return dias


async def obtener_clima(
    ciudad: str,
    fecha_inicio: str,
    fecha_fin: str,
    iata: str | None = None,
) -> dict | None:
    """
    Clima del destino para los días exactos del viaje.

    - Días dentro del horizonte de pronóstico (≤16 días desde hoy): pronóstico real.
    - Días más allá: clima típico (promedio de los últimos años, datos reales).
    - Viajes que cruzan el límite: mezcla de ambos con precision 'parcial'.

    Devuelve None si no se pudo obtener nada — nunca lanza excepción.
    """
    try:
        coords = await resolver_coords(ciudad, iata=iata)
        if not coords:
            logger.warning(f"No se pudieron resolver coordenadas para '{ciudad}'")
            return None
        lat, lon = coords

        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        if fin < inicio:
            return None

        # Limitar la cantidad de días mostrados
        aviso = None
        if (fin - inicio).days + 1 > _MAX_DIAS:
            fin = inicio + timedelta(days=_MAX_DIAS - 1)
            aviso = f"Mostrando el clima de los primeros {_MAX_DIAS} días del viaje."

        limite_forecast = date.today() + timedelta(days=_DIAS_FORECAST)

        dias: list[dict] = []
        precision = None

        if fin <= limite_forecast:
            # Todo el viaje dentro del horizonte de pronóstico
            try:
                dias = await _obtener_pronostico(lat, lon, inicio.isoformat(), fin.isoformat())
                precision = "pronostico"
            except ExternalAPIError:
                cache_key = f"weather:forecast:{round(lat, 2)}:{round(lon, 2)}:{inicio.isoformat()}:{fin.isoformat()}"
                stale = cache_get_stale(cache_key)
                if stale:
                    dias, precision = stale, "stale"
                else:
                    dias = await _obtener_tipico(lat, lon, inicio.isoformat(), fin.isoformat())
                    precision = "tipico"
        elif inicio > limite_forecast:
            # Viaje completamente fuera del horizonte: clima típico
            dias = await _obtener_tipico(lat, lon, inicio.isoformat(), fin.isoformat())
            precision = "tipico"
            aviso = aviso or "Fechas lejanas: mostramos el clima típico de esos días según años anteriores."
        else:
            # Mixto: pronóstico hasta el límite + clima típico para el resto
            try:
                parte_forecast = await _obtener_pronostico(
                    lat, lon, inicio.isoformat(), limite_forecast.isoformat()
                )
            except ExternalAPIError:
                parte_forecast = []
            parte_tipico = await _obtener_tipico(
                lat, lon, (limite_forecast + timedelta(days=1)).isoformat(), fin.isoformat()
            )
            dias = parte_forecast + parte_tipico
            precision = "parcial" if parte_forecast else "tipico"
            if parte_forecast:
                aviso = aviso or (
                    f"Los días posteriores al {limite_forecast.strftime('%d/%m')} "
                    "muestran el clima típico de años anteriores."
                )

        if not dias:
            return None

        return {
            "ciudad": ciudad,
            "lat": lat,
            "lon": lon,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "dias": dias,
            "precision": precision,
            "aviso": aviso,
        }
    except Exception as e:
        logger.warning(f"Error obteniendo clima para '{ciudad}': {e}")
        return None
