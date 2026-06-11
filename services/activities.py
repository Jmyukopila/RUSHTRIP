# services/activities.py
# Servicio de mejores actividades del destino via OpenTripMap (key gratuita opcional)
# Estrategia: cache SQLite → OpenTripMap → cache stale → selección curada local
#
# Las actividades son recomendaciones informativas: no entran en el cálculo del
# presupuesto del plan porque la reserva y el pago se realizan en sitios externos.

import logging
import unicodedata

from core.config import settings
from core.database_cache import cache_get, cache_get_stale, cache_set
from core.errors import ExternalAPIError
from core.http import request_with_retry
from services.weather import resolver_coords

logger = logging.getLogger(__name__)

_RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"

# TTL de cache: los puntos de interés de una ciudad son estables
_TTL_ACTIVIDADES = 7 * 24 * 3600

# Radio de búsqueda alrededor del centro de la ciudad (metros)
_RADIO_M = 12000
_LIMITE_DEFAULT = 8

_AVISO_PRECIOS = (
    "Precios orientativos por tipo de actividad. "
    "La reserva y el pago se realizan en sitios externos."
)

# Mapeo de 'kinds' de OpenTripMap → (categoría en español, emoji, precio estimado USD)
# El orden define la prioridad al clasificar un POI con varios kinds
CATEGORIAS_ACTIVIDAD: list[tuple[tuple[str, ...], tuple[str, str, float]]] = [
    (("amusement_parks", "amusements", "water_parks"), ("Parque de atracciones", "🎢", 50.0)),
    (("museums", "art_galleries"), ("Museo", "🏛️", 15.0)),
    (("theatres_and_entertainments", "cinemas"), ("Espectáculo", "🎭", 40.0)),
    (("view_points", "towers"), ("Mirador", "🌄", 0.0)),
    (("beaches",), ("Playa", "🏖️", 0.0)),
    (("religion", "churches", "cathedrals", "mosques", "synagogues"), ("Templo / Iglesia", "⛪", 0.0)),
    (("gardens_and_parks", "natural", "nature_reserves"), ("Parque / Naturaleza", "🌳", 0.0)),
    (
        ("historic", "historic_architecture", "castles", "fortifications",
         "monuments_and_memorials", "archaeology"),
        ("Sitio histórico", "🏰", 10.0),
    ),
]
_CATEGORIA_DEFAULT = ("Atracción", "📍", 20.0)

# Plantillas de descripción por categoría (la API solo describe en inglés
# y exigiría una llamada extra por POI; generamos el texto en español)
_DESCRIPCIONES: dict[str, str] = {
    "Parque de atracciones": "Diversión para todas las edades en {ciudad}.",
    "Museo":                 "Uno de los museos más destacados de {ciudad}.",
    "Espectáculo":           "Una de las propuestas de entretenimiento más populares de {ciudad}.",
    "Mirador":               "Vistas panorámicas de {ciudad}.",
    "Playa":                 "Una de las playas más conocidas de {ciudad}.",
    "Templo / Iglesia":      "Un sitio religioso emblemático de {ciudad}.",
    "Parque / Naturaleza":   "Un espacio verde ideal para pasear en {ciudad}.",
    "Sitio histórico":       "Parte del patrimonio histórico de {ciudad}.",
    "_default":              "Uno de los lugares más visitados de {ciudad}.",
}

# Selección curada local: (nombre, categoría, emoji, precio estimado USD, descripción)
# Clave IATA en mayúsculas; '_default' para destinos no listados
ACTIVIDADES_CURADAS: dict[str, list[tuple[str, str, str, float, str]]] = {
    "BOG": [
        ("Museo del Oro", "Museo", "🏛️", 5, "La colección de orfebrería prehispánica más grande del mundo."),
        ("Cerro de Monserrate", "Mirador", "🌄", 8, "Vistas panorámicas de toda la ciudad subiendo en teleférico o funicular."),
        ("Tour por La Candelaria", "Tour guiado", "🚶", 15, "Recorrido por el centro histórico, sus calles coloniales y arte urbano."),
        ("Museo Botero", "Museo", "🏛️", 0, "Obras de Fernando Botero y su colección de arte internacional."),
        ("Jardín Botánico de Bogotá", "Parque / Naturaleza", "🌳", 3, "El jardín botánico más grande de Colombia."),
    ],
    "MDE": [
        ("Comuna 13 y sus grafitis", "Tour guiado", "🚶", 20, "El barrio que se transformó a través del arte urbano y las escaleras eléctricas."),
        ("Parque Arví en metrocable", "Parque / Naturaleza", "🌳", 10, "Reserva natural a la que se llega volando sobre la ciudad en metrocable."),
        ("Plaza Botero y Museo de Antioquia", "Museo", "🏛️", 5, "Las esculturas monumentales de Botero al aire libre y su museo."),
        ("Pueblito Paisa", "Sitio histórico", "🏰", 0, "Réplica de un pueblo antioqueño tradicional con mirador sobre la ciudad."),
        ("Guatapé y la Piedra del Peñol", "Excursión", "🚌", 45, "Excursión de día al pueblo más colorido de Colombia y su famosa piedra."),
    ],
    "CTG": [
        ("Ciudad Amurallada", "Sitio histórico", "🏰", 0, "El casco antiguo colonial, sus murallas, balcones y plazas."),
        ("Castillo de San Felipe", "Sitio histórico", "🏰", 7, "La fortaleza española más imponente de América."),
        ("Islas del Rosario", "Excursión", "🚌", 50, "Día de playa y snorkel en un archipiélago de aguas cristalinas."),
        ("Tour al atardecer por Getsemaní", "Tour guiado", "🚶", 15, "El barrio más vibrante de la ciudad, entre arte callejero y plazas."),
        ("Playa de Bocagrande", "Playa", "🏖️", 0, "La playa urbana más popular de Cartagena."),
    ],
    "MEX": [
        ("Museo Nacional de Antropología", "Museo", "🏛️", 5, "El museo más importante de México y su famosa Piedra del Sol."),
        ("Teotihuacán", "Excursión", "🚌", 40, "Las pirámides del Sol y de la Luna a una hora de la ciudad."),
        ("Centro Histórico y el Zócalo", "Sitio histórico", "🏰", 0, "La plaza principal, la Catedral y el Templo Mayor."),
        ("Bosque y Castillo de Chapultepec", "Parque / Naturaleza", "🌳", 4, "El gran pulmón de la ciudad con su castillo en lo alto."),
        ("Trajineras de Xochimilco", "Paseo en barca", "🛶", 25, "Paseo en barcas de colores por los canales con música y comida."),
    ],
    "CUN": [
        ("Chichén Itzá", "Excursión", "🚌", 60, "Una de las siete maravillas del mundo moderno, a día completo desde Cancún."),
        ("Isla Mujeres en ferry", "Excursión", "🚌", 25, "Playas tranquilas y snorkel a 20 minutos en ferry."),
        ("Playa Delfines", "Playa", "🏖️", 0, "La playa pública más famosa de la zona hotelera."),
        ("Parque Xcaret", "Parque de atracciones", "🎢", 110, "Parque ecológico con ríos subterráneos, fauna y espectáculos."),
        ("Cenotes de la Riviera Maya", "Parque / Naturaleza", "🌳", 30, "Nado en pozas naturales de agua dulce únicas de la península."),
    ],
    "MIA": [
        ("South Beach y Ocean Drive", "Playa", "🏖️", 0, "La playa y el paseo art déco más icónicos de la ciudad."),
        ("Wynwood Walls", "Museo", "🎨", 12, "El museo de arte urbano al aire libre más famoso del mundo."),
        ("Tour por Little Havana", "Tour guiado", "🚶", 25, "Cultura cubana, café y música en la Calle Ocho."),
        ("Everglades en hidrodeslizador", "Excursión", "🚌", 40, "Safari en aerodeslizador entre caimanes y manglares."),
        ("Paseo en barco por Biscayne Bay", "Paseo en barco", "🛥️", 30, "La bahía, el skyline y las mansiones de las islas desde el agua."),
    ],
    "MCO": [
        ("Walt Disney World", "Parque de atracciones", "🎢", 110, "El complejo de parques temáticos más visitado del mundo."),
        ("Universal Orlando", "Parque de atracciones", "🎢", 110, "Los parques de Universal y el mundo mágico de Harry Potter."),
        ("Kennedy Space Center", "Museo", "🏛️", 75, "El centro espacial de la NASA con cohetes y transbordadores reales."),
        ("ICON Park", "Atracción", "📍", 30, "Noria gigante, restaurantes y entretenimiento en International Drive."),
        ("Lake Eola Park", "Parque / Naturaleza", "🌳", 0, "El parque del centro de Orlando, ideal para un paseo al atardecer."),
    ],
    "JFK": [
        ("Central Park", "Parque / Naturaleza", "🌳", 0, "El parque urbano más famoso del mundo, en pleno Manhattan."),
        ("Museo Metropolitano (The Met)", "Museo", "🏛️", 30, "Uno de los museos de arte más grandes e importantes del planeta."),
        ("Estatua de la Libertad y Ellis Island", "Excursión", "⛴️", 25, "Ferry a los dos símbolos de la llegada a América."),
        ("Espectáculo en Broadway", "Espectáculo", "🎭", 80, "Un musical en los teatros más famosos del mundo."),
        ("Puente de Brooklyn", "Mirador", "🌄", 0, "Cruce a pie con las mejores vistas del skyline de Manhattan."),
    ],
    "LIM": [
        ("Centro Histórico y Plaza de Armas", "Sitio histórico", "🏰", 0, "El corazón colonial de Lima, Patrimonio de la Humanidad."),
        ("Museo Larco", "Museo", "🏛️", 10, "Arte precolombino en una casona virreinal rodeada de jardines."),
        ("Malecón de Miraflores", "Mirador", "🌄", 0, "Paseo sobre los acantilados con vista al Pacífico y parapentes."),
        ("Circuito Mágico del Agua", "Parque / Naturaleza", "🌳", 4, "Fuentes monumentales con espectáculo de luces por la noche."),
        ("Tour gastronómico por Barranco", "Tour gastronómico", "🍷", 35, "La mejor cocina del mundo en el barrio bohemio de la ciudad."),
    ],
    "MAD": [
        ("Museo del Prado", "Museo", "🏛️", 17, "Una de las pinacotecas más importantes del mundo: Velázquez, Goya, El Bosco."),
        ("Parque del Retiro", "Parque / Naturaleza", "🌳", 0, "El gran parque del centro con su estanque y el Palacio de Cristal."),
        ("Palacio Real", "Sitio histórico", "🏰", 14, "El palacio real más grande de Europa occidental."),
        ("Tour de tapas por La Latina", "Tour gastronómico", "🍷", 40, "Ruta de tabernas centenarias y tapas por el Madrid castizo."),
        ("Estadio Santiago Bernabéu", "Atracción", "📍", 30, "Tour por el estadio y el museo del Real Madrid."),
    ],
    "BCN": [
        ("Sagrada Familia", "Sitio histórico", "🏰", 30, "La obra maestra inacabada de Gaudí, símbolo de la ciudad."),
        ("Park Güell", "Parque / Naturaleza", "🌳", 11, "El parque modernista de Gaudí con vistas a toda Barcelona."),
        ("Tour por el Barrio Gótico", "Tour guiado", "🚶", 15, "Callejuelas medievales, la Catedral y dos mil años de historia."),
        ("Casa Batlló", "Sitio histórico", "🏰", 25, "La casa más fantástica del modernismo en el Paseo de Gracia."),
        ("Playa de la Barceloneta", "Playa", "🏖️", 0, "La playa urbana más animada de la ciudad."),
    ],
    "CDG": [
        ("Museo del Louvre", "Museo", "🏛️", 24, "El museo más visitado del mundo y la Mona Lisa."),
        ("Torre Eiffel", "Mirador", "🌄", 30, "Subida al símbolo de París con vistas de toda la ciudad."),
        ("Paseo en barco por el Sena", "Paseo en barco", "🛥️", 18, "Los monumentos de París vistos desde el río al atardecer."),
        ("Montmartre y el Sacré-Cœur", "Tour guiado", "🚶", 0, "El barrio de los pintores y la basílica con la mejor vista de París."),
        ("Palacio de Versalles", "Excursión", "🚌", 25, "El palacio y los jardines del Rey Sol, a 40 minutos de París."),
    ],
    "FCO": [
        ("Coliseo y Foro Romano", "Sitio histórico", "🏰", 20, "El anfiteatro más famoso del mundo y el corazón de la antigua Roma."),
        ("Museos Vaticanos y Capilla Sixtina", "Museo", "🏛️", 22, "Los frescos de Miguel Ángel y una de las colecciones de arte más grandes."),
        ("Fontana di Trevi y centro histórico", "Tour guiado", "🚶", 0, "Paseo por el Panteón, Piazza Navona y la fuente más famosa del mundo."),
        ("Galería Borghese", "Museo", "🏛️", 15, "Berninis y Caravaggios en una villa rodeada de jardines."),
        ("Tour gastronómico por Trastevere", "Tour gastronómico", "🍷", 45, "Pasta, vino y gelato en el barrio más auténtico de Roma."),
    ],
    "LHR": [
        ("Museo Británico", "Museo", "🏛️", 0, "La piedra Rosetta y tesoros de todas las civilizaciones, con entrada gratuita."),
        ("Torre de Londres", "Sitio histórico", "🏰", 40, "Mil años de historia y las Joyas de la Corona."),
        ("London Eye", "Mirador", "🌄", 35, "La noria sobre el Támesis con vistas del Parlamento y el Big Ben."),
        ("Mercado de Camden", "Atracción", "📍", 0, "Mercados alternativos, música y comida del mundo junto al canal."),
        ("Teatro en el West End", "Espectáculo", "🎭", 60, "Un musical en el distrito teatral más famoso de Europa."),
    ],
    "_default": [
        ("Tour guiado por el centro histórico", "Tour guiado", "🚶", 20, "La mejor forma de orientarte y conocer la historia del destino el primer día."),
        ("Museo principal de la ciudad", "Museo", "🏛️", 15, "La colección más importante del destino para entender su cultura."),
        ("Tour gastronómico local", "Tour gastronómico", "🍷", 35, "Prueba los platos típicos de la mano de un guía local."),
        ("Parque o paseo emblemático", "Parque / Naturaleza", "🌳", 0, "El espacio verde o paseo favorito de los locales."),
        ("Excursión de día completo a los alrededores", "Excursión", "🚌", 50, "Descubre los paisajes y pueblos cercanos al destino."),
    ],
}

# Nombre de ciudad normalizado → clave IATA del dataset curado
# (cubre aeropuertos secundarios como ORY/LGW que comparten ciudad)
_IATA_POR_CIUDAD: dict[str, str] = {
    "bogota": "BOG", "medellin": "MDE", "cartagena": "CTG",
    "ciudad de mexico": "MEX", "cancun": "CUN", "miami": "MIA",
    "orlando": "MCO", "nueva york": "JFK", "new york": "JFK",
    "lima": "LIM", "madrid": "MAD", "barcelona": "BCN",
    "paris": "CDG", "roma": "FCO", "rome": "FCO",
    "londres": "LHR", "london": "LHR",
}


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar nombres de ciudad."""
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_acentos.strip().lower()


def _links_afiliado(ciudad: str) -> dict:
    """Links de afiliado Klook/KKday para reservar actividades en la ciudad."""
    destino = ciudad.lower().replace(" ", "-")
    link_klook = f"https://klook.tpo.li/GBfSCVf0?dest={destino}"
    return {
        "link_reserva": link_klook,
        "link_klook":   link_klook,
        "link_kkday":   f"https://kkday.tpo.li/zHk5IFqZ?dest={destino}",
    }


def _clasificar_kinds(kinds: str) -> tuple[str, str, float]:
    """Clasifica el string 'kinds' de OpenTripMap en (categoría, emoji, precio estimado)."""
    tokens = {k.strip() for k in kinds.split(",") if k.strip()}
    for claves, categoria in CATEGORIAS_ACTIVIDAD:
        if tokens.intersection(claves):
            return categoria
    return _CATEGORIA_DEFAULT


def _descripcion_por_categoria(categoria: str, ciudad: str) -> str:
    """Descripción en español según la categoría de la actividad."""
    plantilla = _DESCRIPCIONES.get(categoria, _DESCRIPCIONES["_default"])
    return plantilla.format(ciudad=ciudad)


def _armar_actividad(
    nombre: str,
    categoria: str,
    icono: str,
    precio: float,
    descripcion: str,
    ciudad: str,
    fuente: str,
) -> dict:
    """Construye el dict plano de una actividad con precio, links y descripción."""
    return {
        "nombre":          nombre,
        "categoria":       categoria,
        "icono":           icono,
        "descripcion":     descripcion,
        "precio_estimado": float(precio),
        "gratis":          precio == 0,
        "moneda":          "USD",
        "fuente":          fuente,
        **_links_afiliado(ciudad),
    }


def _actividades_curadas(ciudad: str, iata: str | None, limite: int) -> dict:
    """Selección curada local: por IATA, por nombre de ciudad o '_default'."""
    key = (iata or "").upper()
    entradas = ACTIVIDADES_CURADAS.get(key)
    if not entradas:
        key = _IATA_POR_CIUDAD.get(_normalizar(ciudad), "")
        entradas = ACTIVIDADES_CURADAS.get(key, ACTIVIDADES_CURADAS["_default"])

    actividades = [
        _armar_actividad(nombre, categoria, icono, precio, descripcion, ciudad, fuente="curado")
        for nombre, categoria, icono, precio, descripcion in entradas[:limite]
    ]
    return {
        "ciudad":      ciudad,
        "actividades": actividades,
        "precision":   "estimada",
        "aviso":       f"Selección curada por RushTrip. {_AVISO_PRECIOS}",
    }


async def _consultar_opentripmap(lat: float, lon: float, ciudad: str, limite: int) -> list[dict]:
    """
    Mejores POIs turísticos alrededor del centro de la ciudad, ordenados por
    relevancia ('rate' de OpenTripMap). Lanza ExternalAPIError si la API falla.
    """
    resp = await request_with_retry(
        "GET", _RADIUS_URL,
        provider="opentripmap",
        max_retries=1,
        params={
            "radius": _RADIO_M,
            "lon":    lon,
            "lat":    lat,
            "kinds":  "interesting_places,amusements,museums",
            "rate":   2,
            "limit":  limite * 3,
            "format": "json",
            "apikey": settings.opentripmap_api_key,
        },
    )
    if resp.status_code != 200:
        raise ExternalAPIError(
            f"OpenTripMap respondió HTTP {resp.status_code}",
            provider="opentripmap",
            status_code=resp.status_code,
        )

    actividades = []
    vistos: set[str] = set()
    pois = sorted(resp.json(), key=lambda p: p.get("rate", 0), reverse=True)
    for poi in pois:
        nombre = (poi.get("name") or "").strip()
        if not nombre or nombre.lower() in vistos:
            continue
        vistos.add(nombre.lower())
        categoria, icono, precio = _clasificar_kinds(poi.get("kinds", ""))
        actividades.append(_armar_actividad(
            nombre, categoria, icono, precio,
            _descripcion_por_categoria(categoria, ciudad),
            ciudad, fuente="opentripmap",
        ))
        if len(actividades) >= limite:
            break
    return actividades


async def obtener_actividades(
    ciudad: str,
    iata: str | None = None,
    limite: int = _LIMITE_DEFAULT,
) -> dict:
    """
    Mejores actividades del destino.

    Cascada: cache → OpenTripMap (si hay key) → cache stale → selección curada.
    Siempre devuelve un dict con 'ciudad', 'actividades', 'precision' y 'aviso' —
    nunca lanza excepción ni devuelve la lista vacía.
    """
    ciudad_limpia = ciudad.strip()
    cache_key = f"actividades:{ciudad_limpia.lower()}:{limite}"

    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        if settings.opentripmap_api_key:
            coords = await resolver_coords(ciudad_limpia, iata=iata)
            if coords:
                lat, lon = coords
                try:
                    actividades = await _consultar_opentripmap(lat, lon, ciudad_limpia, limite)
                    if actividades:
                        resultado = {
                            "ciudad":      ciudad_limpia,
                            "actividades": actividades,
                            "precision":   "real",
                            "aviso":       _AVISO_PRECIOS,
                        }
                        cache_set(cache_key, resultado, provider="opentripmap", ttl_seconds=_TTL_ACTIVIDADES)
                        return resultado
                except ExternalAPIError as e:
                    logger.warning(f"OpenTripMap falló para '{ciudad_limpia}': {e}")
                    stale = cache_get_stale(cache_key)
                    if stale:
                        stale["precision"] = "stale"
                        stale["aviso"] = f"Mostrando actividades guardadas previamente. {_AVISO_PRECIOS}"
                        return stale
    except Exception as e:
        logger.warning(f"Error obteniendo actividades para '{ciudad_limpia}': {e}")

    return _actividades_curadas(ciudad_limpia, iata, limite)
