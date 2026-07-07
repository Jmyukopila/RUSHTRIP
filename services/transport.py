# services/transport.py
# Servicio de transporte terrestre (bus y tren) como alternativa al avión
# Estrategia: cache SQLite → API real (hook futuro, hoy no hay API pública
# gratuita de bus/tren) → estimación local por distancia (Haversine)

import logging
import random
from urllib.parse import quote

from core.database_cache import cache_get, cache_set
from services.flights import AEROPUERTO_COORDS, _distancia_km
from services.cars import CITY_COORDS

logger = logging.getLogger(__name__)

# Medios de transporte terrestre soportados
MEDIOS = ("bus", "tren")

# Distancia máxima (km, gran círculo por trayecto) considerada viable por medio
LIMITE_KM = {"bus": 1500, "tren": 2500}

# Tarifa estimada en USD por km por pasajero
TARIFA_USD_KM = {"bus": 0.055, "tren": 0.09}

# Piso de precio por trayecto: ningún ticket baja de esto aunque la ruta sea corta
PRECIO_MINIMO_TRAYECTO = {"bus": 12.0, "tren": 18.0}

# Velocidad media puerta a puerta para estimar duración
VELOCIDAD_KMH = {"bus": 75, "tren": 110}

# Factor de emisión: kg CO2 por pasajero-km (avión: 0.115 en services/flights)
CO2_KG_PAX_KM = {"bus": 0.027, "tren": 0.014}

# Factor sobre el precio mínimo de vuelo cuando no hay coords para estimar por
# distancia (usado por precio_transporte_minimo para el presupuesto mínimo)
_FACTOR_SIN_COORDS = {"bus": 0.35, "tren": 0.55}

# TTL corto para estimados: permite reintentar una API real pronto
_CACHE_TTL_ESTIMADO = 600

# Nombres genéricos de operadoras para las opciones estimadas
OPERADORAS = {
    "bus": [
        "FlixBus u operadores locales",
        "Líneas interurbanas de bus",
        "Servicios exprés de bus",
        "Operadores regionales de bus",
    ],
    "tren": [
        "Renfe, SNCF u operadores locales",
        "Trenes de alta velocidad",
        "Trenes interurbanos",
        "Trenes regionales",
    ],
}

DESCRIPCION_MEDIO = {
    "bus": "Servicio de bus interurbano. Precio estimado según la distancia de la ruta.",
    "tren": "Servicio de tren interurbano. Precio estimado según la distancia de la ruta.",
}


def _coords(iata: str) -> tuple[float, float] | None:
    """
    Coordenadas (lat, lng) para un IATA: primero aeropuertos, luego ciudades.
    Excluye el "_default" de CITY_COORDS porque una coordenada genérica
    falsearía la distancia de la ruta.
    """
    codigo = iata.upper()
    if codigo in AEROPUERTO_COORDS:
        return AEROPUERTO_COORDS[codigo]
    if codigo in CITY_COORDS and not codigo.startswith("_"):
        return CITY_COORDS[codigo]
    return None


def ruta_viable(medio: str, origen: str, destino: str) -> tuple[bool, float | None]:
    """
    Indica si una ruta es viable en el medio dado según su distancia.

    Returns:
        (viable, distancia_km). Sin coordenadas para algún extremo la ruta
        no es verificable → (False, None).
    """
    coords_o = _coords(origen)
    coords_d = _coords(destino)
    if not coords_o or not coords_d:
        return (False, None)
    km = round(_distancia_km(*coords_o, *coords_d), 1)
    return (km <= LIMITE_KM[medio], km)


def estimar_co2_transporte(medio: str, km: float) -> float:
    """Huella de carbono en kg CO2 por pasajero para un trayecto terrestre."""
    return round(km * CO2_KG_PAX_KM[medio], 1)


def link_compra_transporte(medio: str, origen: str, destino: str) -> str:
    """
    Link de búsqueda de la ruta en Rome2Rio (cubre bus y tren, por nombre de
    ciudad). Centralizado aquí para poder cambiar a un programa de afiliados
    (Omio/12Go) sin tocar el resto del servicio.
    """
    from services.plan import _ciudad_desde_iata

    ciudad_o = quote(_ciudad_desde_iata(origen))
    ciudad_d = quote(_ciudad_desde_iata(destino))
    return f"https://www.rome2rio.com/es/map/{ciudad_o}/{ciudad_d}"


def precio_transporte_minimo(medio: str, origen: str, destino: str) -> float:
    """
    Precio mínimo estimado ida y vuelta por pasajero para el medio dado.
    Usado por calcular_presupuesto_minimo (sin llamadas externas).
    """
    _, km = ruta_viable(medio, origen, destino)
    if km is None:
        from services.plan import _precio_vuelo_minimo
        return round(_precio_vuelo_minimo(destino) * _FACTOR_SIN_COORDS[medio], 2)
    trayecto = max(km * TARIFA_USD_KM[medio], PRECIO_MINIMO_TRAYECTO[medio])
    return round(trayecto * 2, 2)


def _cache_key(medio: str, origen: str, destino: str, fecha_salida: str, fecha_regreso: str, pasajeros: int) -> str:
    """Genera key única para cache de transporte terrestre."""
    return f"transport:{medio}:{origen.upper()}:{destino.upper()}:{fecha_salida}:{fecha_regreso}:{pasajeros}"


async def _buscar_transporte_api(medio, origen, destino, fecha_salida, fecha_regreso, pasajeros) -> dict | None:
    """
    Hook para una API real de bus/tren. Hoy no hay proveedor configurado:
    devuelve None y la cascada cae a la estimación local.
    """
    return None


def _estimar_transporte(
    medio: str, origen: str, destino: str, km: float,
    fecha_salida: str, fecha_regreso: str, pasajeros: int,
) -> dict:
    """
    Genera opciones estimadas de bus/tren por distancia, en el mismo formato
    que los vuelos para que el plan y el frontend las consuman sin cambios.
    """
    trayecto_base = max(km * TARIFA_USD_KM[medio], PRECIO_MINIMO_TRAYECTO[medio])
    precio_base = trayecto_base * 2  # ida y vuelta
    duracion_base = int(km / VELOCIDAD_KMH[medio] * 60) + 30  # +30 min de terminal
    co2_kg = estimar_co2_transporte(medio, km)
    link = link_compra_transporte(medio, origen, destino)

    opciones = []
    for i, operadora in enumerate(OPERADORAS[medio]):
        escalas = 0 if i == 0 else (1 if i < 3 else 2)
        # Las opciones con paradas tardan más pero suelen ser más baratas
        factor_precio = random.uniform(0.85, 1.15) * (1 - 0.05 * escalas)
        pax_precio = round(precio_base * factor_precio, 2)
        opciones.append({
            "aerolinea":          "",  # sin código IATA: no matchea el filtro premium
            "aerolinea_nombre":   operadora,
            "descripcion":        DESCRIPCION_MEDIO[medio],
            "logo_url":           "",
            "salida":             fecha_salida,
            "regreso":            fecha_regreso,
            "origen":             origen.upper(),
            "destino":            destino.upper(),
            "medio":              medio,
            "distancia_km":       km,
            "duracion_minutos":   duracion_base + escalas * 45,
            "escalas":            escalas,
            "escalas_texto":      "Directo" if escalas == 0 else f"{escalas} parada{'s' if escalas > 1 else ''}",
            "precio_por_persona": pax_precio,
            "precio_total":       round(pax_precio * pasajeros, 2),
            "pasajeros":          pasajeros,
            "co2_kg":             co2_kg,
            "link_compra":        link,
            "tipo":               "estimado",
        })

    opciones.sort(key=lambda o: o["precio_por_persona"])

    logger.info(f"Opciones de {medio} estimadas para {origen}→{destino} (~{km:.0f} km): {len(opciones)}")

    return {
        "aviso": f"Precios estimados por distancia para {medio}; los horarios y tarifas reales dependen de la operadora.",
        "precision": "estimada",
        "opciones": opciones,
    }


async def buscar_transporte(
    medio: str,
    origen: str,
    destino: str,
    fecha_salida: str,
    fecha_regreso: str,
    pasajeros: int = 1,
) -> dict:
    """
    Busca opciones de transporte terrestre (bus o tren) para una ruta.

    Cascada: cache → API real (hook futuro) → estimación local por distancia.
    Ruta no viable o sin coordenadas → opciones vacías con aviso en español
    (quien orquesta decide la degradación, p. ej. el plan cae a avión).

    Returns:
        Dict con aviso, precision y opciones (mismo contrato que los vuelos
        + campos medio y distancia_km)
    """
    medio = medio.strip().lower()
    if medio not in MEDIOS:
        raise ValueError(f"Medio de transporte no soportado: {medio}")

    origen = origen.upper()
    destino = destino.upper()

    viable, km = ruta_viable(medio, origen, destino)
    if not viable:
        if km is None:
            aviso = f"No hay datos de ruta terrestre para {origen}→{destino}."
        else:
            aviso = f"La ruta {origen}→{destino} (~{km:.0f} km) no es viable en {medio}."
        return {"aviso": aviso, "precision": "estimada", "opciones": []}

    key = _cache_key(medio, origen, destino, fecha_salida, fecha_regreso, pasajeros)
    cacheado = cache_get(key)
    if cacheado:
        return cacheado

    resultado_api = await _buscar_transporte_api(medio, origen, destino, fecha_salida, fecha_regreso, pasajeros)
    if resultado_api:
        cache_set(key, resultado_api, provider="transporte", ttl_seconds=6 * 3600)
        return resultado_api

    resultado = _estimar_transporte(medio, origen, destino, km, fecha_salida, fecha_regreso, pasajeros)
    cache_set(key, resultado, provider="reference", ttl_seconds=_CACHE_TTL_ESTIMADO)
    return resultado
