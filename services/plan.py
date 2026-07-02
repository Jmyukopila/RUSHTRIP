# services/plan.py
# Servicio de generación de planes de viaje optimizados por presupuesto
# Combina búsquedas de vuelos, hoteles y coches para crear el mejor plan

import asyncio
import logging
import re
from core.config import settings
from services.flights import buscar_vuelos
from services.hotels  import buscar_hoteles, _calcular_noches, PRECIO_REFERENCIA_HOTEL
from services.cars    import buscar_coches
from services.airports import aeropuertos_alternativos, buscar_aeropuerto

logger = logging.getLogger(__name__)

# Cache simple para resoluciones ciudad → IATA (evita pegar a API repetidamente)
_RESOLUCIONES_CACHE: dict[str, str] = {}

async def resolver_iata(texto: str) -> str:
    """
    Convierte un texto (ciudad o IATA) en un código IATA de 3 letras.

    Si el texto ya parece un código IATA (3 letras), lo devuelve tal cual.
    Si no, busca aeropuertos con la API y devuelve el primer resultado.

    Args:
        texto: Nombre de ciudad o código IATA

    Returns:
        Código IATA de 3 letras en mayúsculas

    Raises:
        ValueError: Si no se encuentra ningún aeropuerto para el texto dado
    """
    limpio = texto.strip().upper()

    # Si ya es un IATA válido de 3 letras, devolverlo directamente
    if re.match(r"^[A-Z]{3}$", limpio):
        return limpio

    # Verificar cache local
    if limpio in _RESOLUCIONES_CACHE:
        return _RESOLUCIONES_CACHE[limpio]

    # Llamar API de aeropuertos para resolver
    resultados = await buscar_aeropuerto(limpio)
    if resultados and len(resultados) > 0:
        iata = resultados[0]["codigo"]
        _RESOLUCIONES_CACHE[limpio] = iata
        return iata

    raise ValueError(f"No se encontró aeropuerto para: {texto}")

# Mapeo IATA → nombre de ciudad para buscar hoteles
# Necesario porque la API de hoteles busca por nombre de ciudad, no por IATA
IATA_A_CIUDAD: dict[str, str] = {
    # Colombia
    "BOG": "Bogotá", "MDE": "Medellín", "CLO": "Cali",
    "CTG": "Cartagena", "BAQ": "Barranquilla",
    # LATAM
    "MIA": "Miami", "CUN": "Cancún", "MEX": "Ciudad de México",
    "GDL": "Guadalajara", "LIM": "Lima", "GYE": "Guayaquil",
    "UIO": "Quito", "SCL": "Santiago", "EZE": "Buenos Aires",
    "GRU": "São Paulo", "SDQ": "Santo Domingo", "HAV": "La Habana",
    "PTY": "Panamá", "SJO": "San José", "BZE": "Belice",
    "SAL": "San Salvador", "MGA": "Managua", "TGU": "Tegucigalpa",
    # Norte America
    "JFK": "Nueva York", "LAX": "Los Ángeles", "ORD": "Chicago",
    "MCO": "Orlando", "LAS": "Las Vegas", "SFO": "San Francisco",
    "BOS": "Boston", "DCA": "Washington", "ATL": "Atlanta",
    "SEA": "Seattle", "DEN": "Denver", "IAH": "Houston",
    "DFW": "Dallas", "YYZ": "Toronto", "YVR": "Vancouver",
    # Europa
    "MAD": "Madrid", "BCN": "Barcelona", "LHR": "Londres",
    "CDG": "París", "FCO": "Roma", "AMS": "Ámsterdam",
    "FRA": "Fráncfort", "LIS": "Lisboa", "VIE": "Viena",
    "ZRH": "Zúrich", "MXP": "Milán", "DUB": "Dublín",
    "BRU": "Bruselas", "BER": "Berlín", "MUC": "Múnich",
    "ORY": "París", "LGW": "Londres", "STN": "Londres",
    # Asia / Medio Oriente
    "DXB": "Dubái", "SIN": "Singapur", "BKK": "Bangkok",
    "HND": "Tokio", "NRT": "Tokio", "ICN": "Seúl",
    "HKG": "Hong Kong", "KUL": "Kuala Lumpur", "DEL": "Delhi",
    "BOM": "Mumbai", "DOH": "Doha", "AUH": "Abu Dabi",
    "IST": "Estambul", "TLV": "Tel Aviv",
    # Oceania
    "SYD": "Sídney", "MEL": "Melbourne", "AKL": "Auckland",
    # Africa
    "JNB": "Johannesburgo", "CPT": "Ciudad del Cabo", "CAI": "El Cairo",
    "CMN": "Casablanca", "NBO": "Nairobi",
}

# Precio promedio por noche (importado de services/hotels para evitar duplicacion)

# Precios de referencia mínimos de vuelo (ida y vuelta) por destino
# Usados para calcular el presupuesto mínimo sugerido
PRECIO_VUELO_MINIMO: dict[str, float] = {
    # Colombia (doméstico/regional)
    "BOG": 120, "MDE": 120, "CLO": 120, "CTG": 150, "BAQ": 120,
    "SMR": 120, "EOH": 120, "ADZ": 180,
    # LATAM
    "MIA": 220, "CUN": 180, "MEX": 200, "GDL": 200, "LIM": 180,
    "GYE": 160, "UIO": 160, "SCL": 280, "EZE": 320, "GRU": 280,
    "SDQ": 220, "HAV": 220, "PTY": 180, "SJO": 200,
    # USA
    "JFK": 320, "LAX": 420, "ORD": 320, "MCO": 280, "LAS": 320,
    "SFO": 420, "BOS": 380, "DCA": 320, "ATL": 280, "SEA": 380,
    "DEN": 350, "IAH": 280, "DFW": 280,
    # Europa
    "MAD": 480, "BCN": 480, "LHR": 520, "CDG": 520, "FCO": 480,
    "AMS": 520, "FRA": 480, "LIS": 420, "VIE": 480, "ZRH": 580,
    "MXP": 480, "DUB": 480, "BRU": 480, "BER": 480, "MUC": 500,
    # Default
    "_default": 280,
}


def _precio_vuelo_minimo(iata_destino: str) -> float:
    """Obtiene el precio de vuelo mínimo estimado para un destino."""
    return PRECIO_VUELO_MINIMO.get(
        iata_destino.upper(),
        PRECIO_VUELO_MINIMO["_default"]
    )


# Factores de presupuesto por tier. El presupuesto base (vuelo + hotel + coche)
# ya varía por país vía los precios de referencia; estos factores lo ajustan por
# nivel de calidad y definen cuánto margen hay hasta el máximo sugerido:
#   - vuelo/hotel/coche: escalan el mínimo (económico más barato, premium más caro)
#   - max_ratio: multiplica el subtotal ajustado para obtener el máximo del tier
#     (económico tiene poco margen; premium mucho, porque hoteles/vuelos de gama
#      alta varían más de precio)
TIER_PRESUPUESTO_FACTORES: dict[str, dict[str, float]] = {
    "economico": {"vuelo": 0.9, "hotel": 0.7, "coche": 0.8, "max_ratio": 1.8},
    "estandar":  {"vuelo": 1.0, "hotel": 1.0, "coche": 1.0, "max_ratio": 2.4},
    "premium":   {"vuelo": 1.3, "hotel": 2.0, "coche": 1.6, "max_ratio": 3.2},
}


def calcular_presupuesto_minimo(
    origen: str, destino: str, noches: int, pasajeros: int,
    incluir_hotel: bool = True, incluir_vehiculo: bool = False,
    tier: str = "estandar",
) -> dict:
    """
    Calcula un presupuesto mínimo y máximo sugerido basado en precios de
    referencia. No hace llamadas a APIs externas — solo usa datos estáticos.

    La fórmula varía por país (precios de referencia por destino) y por tier
    (factores en TIER_PRESUPUESTO_FACTORES):
      - Vuelo:  PRECIO_VUELO_MINIMO[destino] * pasajeros * factor_vuelo
      - Hotel:  PRECIO_REFERENCIA_HOTEL[destino] * noches * pasajeros * factor_hotel
      - Coche:  PRECIO_REFERENCIA_COCHE[destino] * noches * factor_coche (si aplica)
      - Mínimo: subtotal + 10% de margen
      - Máximo: subtotal * max_ratio del tier

    Args:
        origen: Código IATA de origen
        destino: Código IATA de destino
        noches: Número de noches de estadía
        pasajeros: Número de pasajeros
        incluir_hotel: Si incluir hotel en el cálculo
        incluir_vehiculo: Si incluir vehículo en el cálculo
        tier: Nivel de calidad ('economico', 'estandar', 'premium')

    Returns:
        Dict con presupuesto_minimo_sugerido, presupuesto_maximo_sugerido y desglose
    """
    from services.hotels import PRECIO_REFERENCIA_HOTEL

    factores = TIER_PRESUPUESTO_FACTORES.get(tier, TIER_PRESUPUESTO_FACTORES["estandar"])

    vuelo_min = _precio_vuelo_minimo(destino) * pasajeros * factores["vuelo"]

    hotel_min = 0
    if incluir_hotel:
        precio_noche = PRECIO_REFERENCIA_HOTEL.get(
            destino.upper(), PRECIO_REFERENCIA_HOTEL["_default"]
        )
        hotel_min = precio_noche * noches * pasajeros * factores["hotel"]

    coche_min = 0
    if incluir_vehiculo:
        from services.cars import PRECIO_REFERENCIA_COCHE
        precio_dia = PRECIO_REFERENCIA_COCHE.get(
            destino.upper(), PRECIO_REFERENCIA_COCHE["_default"]
        )
        coche_min = precio_dia * noches * factores["coche"]

    subtotal = vuelo_min + hotel_min + coche_min
    minimo = round(subtotal * 1.1, 2)  # Margen del 10%
    maximo = round(subtotal * factores["max_ratio"], 2)

    return {
        "presupuesto_minimo_sugerido": minimo,
        "presupuesto_maximo_sugerido": maximo,
        "tier": tier,
        "desglose": {
            "vuelo_minimo": round(vuelo_min, 2),
            "hotel_minimo": round(hotel_min, 2),
            "coche_minimo": round(coche_min, 2),
            "margen": round(minimo - subtotal, 2),
        },
    }


# Configuración de tiers para diferentes presupuestos
# Cada tier tiene filtros específicos para hoteles y airlines
TIER_CONFIG = {
    # Viaje económico: hoteles básicos, todas las aerolineas
    "economico":  {"estrellas_min": 1, "estrellas_max": 3, "aerolineas_excluir": [],            "coche_orden": "asc"},
    # Viaje estándar: hoteles de 3-4 estrellas, todas las aerolineas
    "estandar":   {"estrellas_min": 3, "estrellas_max": 4, "aerolineas_excluir": [],            "coche_orden": "asc"},
    # Viaje premium: hoteles de 4-5 estrellas, excluye low-cost
    "premium":    {"estrellas_min": 4, "estrellas_max": 5, "aerolineas_excluir": ["NK", "DM", "VH", "P5"], "coche_orden": "desc"},
}


def _ciudad_desde_iata(iata: str) -> str:
    """Convierte código IATA al nombre de ciudad para buscar hoteles."""
    return IATA_A_CIUDAD.get(iata.upper(), iata)


async def _resolver_ciudad_destino(iata: str) -> str:
    """
    Nombre de ciudad para un IATA, resolviendo via autocomplete (cacheado) si
    no está en el mapeo local. Pasar el código crudo a los servicios de hoteles
    hace que el geocoder acierte cualquier cosa (p.ej. 'ZAG' devolvía hoteles
    de Ámsterdam en vez de Zagreb).
    """
    nombre = IATA_A_CIUDAD.get(iata.upper())
    if nombre:
        return nombre
    try:
        resultados = await buscar_aeropuerto(iata)
        if resultados and resultados[0].get("nombre"):
            return resultados[0]["nombre"]
    except Exception as e:
        logger.warning(f"No se pudo resolver nombre de ciudad para {iata}: {e}")
    return iata.upper()


async def _vuelos_flexibles(
    origen: str,
    destino: str,
    fecha_salida: str,
    fecha_regreso: str,
    pasajeros: int,
    duracion_dias: int,
) -> tuple[dict, str, str]:
    """
    Modo flexible: una búsqueda por mes detecta el día de salida más barato
    (los vuelos vienen ordenados por precio) y una búsqueda exacta confirma esa
    ventana. Máximo 2 llamadas a buscar_vuelos, en vez de recorrer ~6 ventanas.

    Returns:
        Tupla (resultado_vuelos, fecha_salida_final, fecha_regreso_final)
    """
    from datetime import datetime as dt, timedelta

    mes = fecha_salida[:7]  # YYYY-MM
    resultado_mes = await buscar_vuelos(origen, destino, mes, mes, pasajeros)
    # Solo cuentan salidas dentro del mes pedido: la cascada de buscar_vuelos
    # puede devolver vuelos de otros meses (nivel "sin fecha") y elegir esas
    # fechas movería el viaje fuera de lo que pidió el usuario.
    vuelos_mes = [
        v for v in (resultado_mes.get("vuelos") or [])
        if (v.get("salida") or "").startswith(mes)
    ]
    if not vuelos_mes:
        resultado = await buscar_vuelos(origen, destino, fecha_salida, fecha_regreso, pasajeros)
        return resultado, fecha_salida, fecha_regreso

    mejor_dia = (vuelos_mes[0].get("salida") or "")[:10]
    try:
        d_salida = dt.strptime(mejor_dia, "%Y-%m-%d")
    except ValueError:
        return resultado_mes, fecha_salida, fecha_regreso

    mejor_salida = mejor_dia
    mejor_regreso = (d_salida + timedelta(days=duracion_dias)).strftime("%Y-%m-%d")

    resultado = resultado_mes
    try:
        res_exacto = await buscar_vuelos(origen, destino, mejor_salida, mejor_regreso, pasajeros)
        if res_exacto.get("vuelos"):
            resultado = res_exacto
    except Exception as e:
        logger.warning(f"Busqueda exacta flexible fallo para {origen}->{destino}: {e}")

    if resultado is resultado_mes:
        resultado["precision"] = "mes"
        resultado["vuelos"] = vuelos_mes  # sin salidas fuera del mes pedido
    resultado["aviso"] = (
        f"Modo flexible: encontramos la mejor fecha para tu viaje de {duracion_dias} dias. "
        f"Salida: {mejor_salida}, Regreso: {mejor_regreso}."
    )
    return resultado, mejor_salida, mejor_regreso


def _precio_hotel_estimado(iata_destino: str) -> float:
    """Obtiene el precio de referencia por noche para un destino."""
    return PRECIO_REFERENCIA_HOTEL.get(
        iata_destino.upper(),
        PRECIO_REFERENCIA_HOTEL["_default"]
    )


def _armar_plan(
    vuelo: dict, noches: int, destino: str, presupuesto: float, pasajeros: int,
    ciudad_nombre: str = "", checkin: str = "", checkout: str = "",
    coches: list | None = None, coche_orden: str = "asc",
    incluir_hotel: bool = True,
) -> dict:
    """
    Construye un plan de viaje combinando vuelo, hotel y opcionalmente coche.

    Args:
        vuelo: Datos del vuelo seleccionado
        noches: Número de noches de estancia
        destino: Código IATA del destino
        presupuesto: Presupuesto total del viaje
        pasajeros: Número de pasajeros
        ciudad_nombre: Nombre legible de la ciudad
        checkin: Fecha de entrada
        checkout: Fecha de salida
        coches: Lista de coches disponibles (opcional)
        coche_orden: Orden para seleccionar coche ('asc' o 'desc')
        incluir_hotel: Si True, incluye costo de hotel

    Returns:
        Dict con el plan completo incluyendo vuelo, hotel, coche y totales
    """
    precio_vuelo = vuelo["precio_total"]

    # Calcular costo de hotel si está habilitado
    if incluir_hotel:
        precio_noche = _precio_hotel_estimado(destino)
        costo_hotel  = round(precio_noche * noches, 2)
    else:
        precio_noche = 0
        costo_hotel  = 0

    # Calcular total y verificar si está dentro del presupuesto
    costo_total  = round(precio_vuelo + costo_hotel, 2)
    dentro       = costo_total <= presupuesto

    # Generar link de búsqueda de hoteles
    link_buscar = (
        f"https://search.hotellook.com/hotels?destination={ciudad_nombre}"
        f"&checkIn={checkin}&checkOut={checkout}"
        f"&adults={pasajeros}&marker={settings.travelpayouts_marker}"
    ) if (ciudad_nombre and incluir_hotel) else ""

    # Construir estructura del plan
    plan = {
        "vuelo": vuelo,
        "hotel": {
            "precio_noche": precio_noche,
            "precio_total": costo_hotel,
            "noches":       noches,
            "criterio":     f"Precio estimado de {precio_noche:.0f} USD/noche para {ciudad_nombre or destino} basado en tarifas promedio de la zona.",
            "link_buscar":  link_buscar,
        },
        "total":              costo_total,
        "presupuesto":        presupuesto,
        "dentro_presupuesto": dentro,
    }

    # Añadir coche si está disponible y es requested
    if coches:
        usado = precio_vuelo + costo_hotel
        restante = presupuesto - usado

        # Seleccionar coche segun el tier: 'desc' (premium) toma el más caro
        # que quepa en el presupuesto restante; 'asc' el más barato
        candidatos = [c for c in coches if c.get("precio_total", 0) <= restante]
        if candidatos:
            elegir = max if coche_orden == "desc" else min
            coche = elegir(candidatos, key=lambda c: c.get("precio_total", 0))
        else:
            # Si ninguno cabe, tomar el más barato y marcarlo
            coche = dict(min(coches, key=lambda c: c.get("precio_total", 0)))
            coche["fuera_presupuesto"] = True

        plan["coche"] = coche
        plan["total"] = round(costo_total + coche.get("precio_total", 0), 2)
        plan["dentro_presupuesto"] = plan["total"] <= presupuesto

    return plan


def _emparejar_hotel(plan: dict, hoteles: list, presupuesto: float) -> dict:
    """
    Reemplaza el hotel estimado por el mejor hotel real disponible
    dentro del presupuesto restante despues del vuelo.

    Devuelve un nuevo plan con el hotel actualizado (no modifica el original).

    Args:
        plan: Plan de viaje original
        hoteles: Lista de hoteles reales disponibles
        presupuesto: Presupuesto total del viaje

    Returns:
        Nuevo dict con hotel actualizado
    """
    costo_vuelo = plan["vuelo"]["precio_total"]
    costo_coche = plan.get("coche", {}).get("precio_total", 0)
    restante = presupuesto - costo_vuelo - costo_coche
    nuevo_plan = dict(plan)

    if not hoteles:
        nuevo_plan["hotel"] = {**nuevo_plan["hotel"], "tipo": "estimado"}
        return nuevo_plan

    # El mejor hotel que quepa en el presupuesto restante (mejor experiencia);
    # si ninguno cabe, el más barato disponible
    candidatos = [h for h in hoteles if h.get("precio_total", 0) <= restante]
    if candidatos:
        mejor = max(candidatos, key=lambda h: h.get("precio_total", 0))
    else:
        mejor = min(hoteles, key=lambda h: h.get("precio_total", 0))
    nuevo_plan["hotel"] = {**mejor, "tipo": "recomendado"}
    nuevo_plan["total"] = round(costo_vuelo + costo_coche + mejor["precio_total"], 2)
    nuevo_plan["dentro_presupuesto"] = nuevo_plan["total"] <= presupuesto
    return nuevo_plan


async def generar_plan(
    origen:          str,
    destino:         str,
    fecha_salida:    str,
    fecha_regreso:   str,
    presupuesto:     float,
    pasajeros:       int = 1,
    incluir_hotel:   bool = True,
    incluir_vehiculo: bool = False,
    tier:            str = "estandar",
    modo:            str = "exacto",
    duracion_dias:   int = 7,
) -> dict:
    """
    Genera un plan de viaje optimizado para el presupuesto dado.

    El proceso:
      1. Busca vuelos disponibles (con fallback en 3 niveles)
      2. Si modo=flexible, prueba varias fechas y elige la mas barata
      3. Busca hoteles reales si incluir_hotel=True
      4. Busca alquiler de coches si incluir_vehiculo=True
      5. Filtra segun tier (excluye low-cost en premium)
      6. Calcula planes para cada vuelo
      7. Empareja cada plan con el mejor hotel disponible
      8. Selecciona el plan optimo (mas caro dentro del presupuesto)

    Args:
        origen: Codigo IATA del aeropuerto de origen
        destino: Codigo IATA del aeropuerto de destino
        fecha_salida: Fecha de salida (YYYY-MM-DD)
        fecha_regreso: Fecha de regreso (YYYY-MM-DD)
        presupuesto: Presupuesto total en USD
        pasajeros: Numero de pasajeros (default: 1)
        incluir_hotel: Si True, incluye busqueda de hoteles (default: True)
        incluir_vehiculo: Si True, incluye busqueda de coches (default: False)
        tier: Nivel de calidad ('economico', 'estandar', 'premium')
        modo: 'exacto' (fechas fijas) o 'flexible' (busca mejor precio en el mes)
        duracion_dias: Dias de estadia para modo flexible

    Returns:
        Dict con plan_optimo, alternativas, hoteles, coches y avisos
    """
    # Calcular noches de estancia
    noches = _calcular_noches(fecha_salida, fecha_regreso)

    # Obtener configuración del tier
    cfg = TIER_CONFIG.get(tier, TIER_CONFIG["estandar"])

    # Convertir IATA a nombre de ciudad para hoteles
    ciudad_destino = await _resolver_ciudad_destino(destino)

    async def _tarea_hoteles(checkin: str, checkout: str) -> dict:
        if not incluir_hotel:
            return {"hoteles": []}
        return await buscar_hoteles(
            ciudad=ciudad_destino,
            checkin=checkin,
            checkout=checkout,
            adultos=pasajeros,
            estrellas_min=cfg["estrellas_min"],
            estrellas_max=cfg["estrellas_max"],
        )

    async def _tarea_coches(pickup: str, dropoff: str) -> dict:
        if not incluir_vehiculo:
            return {"coches": []}
        return await buscar_coches(iata=destino, pickup_date=pickup, dropoff_date=dropoff)

    # 1-2. Buscar vuelos, hoteles y coches.
    # En modo flexible las fechas definitivas dependen del resultado de vuelos,
    # así que hoteles/coches se lanzan después; en modo exacto todo va en paralelo.
    if modo == "flexible":
        resultado_vuelos, fecha_salida, fecha_regreso = await _vuelos_flexibles(
            origen, destino, fecha_salida, fecha_regreso, pasajeros, duracion_dias
        )
        noches = _calcular_noches(fecha_salida, fecha_regreso)
        resultado_hoteles, resultado_coches = await asyncio.gather(
            _tarea_hoteles(fecha_salida, fecha_regreso),
            _tarea_coches(fecha_salida, fecha_regreso),
        )
    else:
        resultado_vuelos, resultado_hoteles, resultado_coches = await asyncio.gather(
            buscar_vuelos(origen, destino, fecha_salida, fecha_regreso, pasajeros),
            _tarea_hoteles(fecha_salida, fecha_regreso),
            _tarea_coches(fecha_salida, fecha_regreso),
        )

    # Extraer datos de los resultados
    vuelos       = resultado_vuelos.get("vuelos", [])
    vuelo_prec   = resultado_vuelos.get("precision", "sin_resultados")
    hotel_prec   = resultado_hoteles.get("precision", "exacta") if isinstance(resultado_hoteles, dict) else "exacta"
    # Los hoteles reportan "real" (precios reales de Hotels.nl); para la
    # precision combinada del plan equivale a "exacta"
    if hotel_prec == "real":
        hotel_prec = "exacta"
    aviso_vuelos = resultado_vuelos.get("aviso")

    # Agregar precision combinada: si ambos son exacta → exacta;
    # si uno es estimada → parcial; si ambos estimada → estimada
    _prec_order = {"exacta": 0, "mes": 1, "aproximada": 2, "parcial": 3, "stale": 4, "estimada": 5}
    prec_values = [vuelo_prec, hotel_prec]
    max_prec = max(prec_values, key=lambda p: _prec_order.get(p, 99))
    min_prec = min(prec_values, key=lambda p: _prec_order.get(p, 99))
    if max_prec == min_prec:
        precision = max_prec
    elif max_prec == "estimada":
        precision = "estimada" if min_prec != "exacta" else "parcial"
    else:
        precision = max_prec

    # Normalizar lista de hoteles (puede venir en diferentes formatos)
    hoteles_lista = resultado_hoteles.get("hoteles", []) if isinstance(resultado_hoteles, dict) else resultado_hoteles or []

    # 3. Filtrar vuelos según tier (excluir low-cost para premium)
    excluir = cfg.get("aerolineas_excluir", [])
    if excluir:
        vuelos_premium = [v for v in vuelos if v.get("aerolinea", "") not in excluir]
        if vuelos_premium:
            vuelos = vuelos_premium

    # Si no hay vuelos, devolver respuesta vacía
    if not vuelos:
        return {
            "origen":         origen.upper(),
            "destino":        destino.upper(),
            "ciudad_destino": ciudad_destino,
            "fecha_salida":   fecha_salida,
            "fecha_regreso":  fecha_regreso,
            "pasajeros":      pasajeros,
            "noches":         noches,
            "presupuesto":    presupuesto,
            "plan_optimo":    None,
            "alternativas":   [],
            "hoteles":        hoteles_lista,
            "coches":         resultado_coches,
            "aviso":          aviso_vuelos or "No se encontraron vuelos para esta ruta.",
            "precision":      precision,
            "clima":          None,
            "actividades":    None,
        }

    # 4. Calcular plan para cada vuelo disponible
    coches_lista = resultado_coches.get("coches", []) if isinstance(resultado_coches, dict) else []
    planes = [
        _armar_plan(v, noches, destino, presupuesto, pasajeros, ciudad_destino, fecha_salida, fecha_regreso, coches_lista, cfg["coche_orden"], incluir_hotel)
        for v in vuelos
    ]

    # 5. Emparejar cada plan con el mejor hotel real segun presupuesto
    planes = [
        _emparejar_hotel(p, hoteles_lista, presupuesto)
        for p in planes
    ]

    # Separar planes que caben en el presupuesto de los que no
    dentro = [p for p in planes if p["dentro_presupuesto"]]
    fuera  = [p for p in planes if not p["dentro_presupuesto"]]

    # 6. Seleccionar plan óptimo
    if dentro:
        # De los que caben, tomar el más caro (mejor experiencia)
        plan_optimo  = max(dentro, key=lambda p: p["total"])
        alternativas = sorted(
            [p for p in dentro if p != plan_optimo],
            key=lambda p: p["total"],
            reverse=True
        )[:2]  # Máximo 2 alternativas
        aviso = aviso_vuelos
    else:
        # Ninguno cabe en el presupuesto, tomar el más económico
        plan_optimo  = min(fuera, key=lambda p: p["total"])
        alternativas = sorted(
            [p for p in fuera if p != plan_optimo],
            key=lambda p: p["total"]
        )[:2]
        # Generar aviso indicando que ningún plan cabe en el presupuesto
        aviso = (
            f"No encontramos combinación dentro de tu presupuesto de ${presupuesto:.0f}. "
            f"La opción más económica disponible cuesta ${plan_optimo['total']:.0f}."
        )
        if aviso_vuelos:
            aviso = aviso_vuelos + " " + aviso

    # 7. Buscar aeropuertos alternativos cercanos al destino (en paralelo)
    alternativas_aeropuerto = []
    cercanos = aeropuertos_alternativos(destino)
    if cercanos:
        async def _vuelo_alternativo(alt: str) -> dict | None:
            try:
                res_alt = await buscar_vuelos(origen, alt, fecha_salida, fecha_regreso, pasajeros)
                if res_alt.get("vuelos"):
                    mejor_alt = min(res_alt["vuelos"], key=lambda v: v["precio_total"])
                    return {
                        "iata": alt,
                        "nombre": _ciudad_desde_iata(alt),
                        "vuelo_mas_barato": mejor_alt["precio_total"],
                        "precision": res_alt.get("precision", "sin_resultados"),
                    }
            except Exception:
                pass
            return None

        resultados_alt = await asyncio.gather(*(_vuelo_alternativo(a) for a in cercanos[:3]))
        alternativas_aeropuerto = [r for r in resultados_alt if r]

    # Calcular presupuesto mínimo sugerido (sin API calls)
    presupuesto_minimo = calcular_presupuesto_minimo(
        origen=origen, destino=destino, noches=noches,
        pasajeros=pasajeros, incluir_hotel=incluir_hotel,
        incluir_vehiculo=incluir_vehiculo, tier=tier,
    )

    # 8. Clima y actividades del destino, en paralelo (no bloquean el plan si fallan)
    clima, actividades = None, None
    try:
        from services.weather import obtener_clima
        from services.activities import obtener_actividades
        clima, actividades = await asyncio.gather(
            obtener_clima(ciudad_destino, fecha_salida, fecha_regreso, iata=destino),
            obtener_actividades(ciudad_destino, iata=destino),
        )
    except Exception as e:
        logger.warning(f"No se pudo obtener clima/actividades para {ciudad_destino}: {e}")

    # Devolver resultado completo
    return {
        "origen":         origen.upper(),
        "destino":        destino.upper(),
        "ciudad_destino": ciudad_destino,
        "fecha_salida":   fecha_salida,
        "fecha_regreso":  fecha_regreso,
        "pasajeros":      pasajeros,
        "noches":         noches,
        "presupuesto":    presupuesto,
        "presupuesto_minimo_sugerido": presupuesto_minimo["presupuesto_minimo_sugerido"],
        "presupuesto_maximo_sugerido": presupuesto_minimo["presupuesto_maximo_sugerido"],
        "plan_optimo":    plan_optimo,
        "alternativas":   alternativas,
        "hoteles":        hoteles_lista,
        "coches":         resultado_coches,
        "aviso":          aviso,
        "precision":      precision,
        "aeropuertos_alternativos": alternativas_aeropuerto,
        "clima":          clima,
        "actividades":    actividades,
    }