# services/activities.py
# Servicio de mejores actividades del destino via OpenTripMap (key gratuita opcional)
# Estrategia: cache SQLite → OpenTripMap → cache stale → selección curada local
#
# Las actividades son recomendaciones informativas: no entran en el cálculo del
# presupuesto del plan porque la reserva y el pago se realizan en sitios externos.

import asyncio
import hashlib
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from statistics import mean
from urllib.parse import urlparse

from core.config import settings
from core.database_cache import cache_get, cache_get_stale, cache_set
from core.errors import ExternalAPIError
from core.http import request_with_retry
from services.weather import resolver_coords

logger = logging.getLogger(__name__)

_RADIUS_URL = "https://api.opentripmap.com/0.1/en/places/radius"

# TTL de cache: los puntos de interés de una ciudad son estables
_TTL_ACTIVIDADES = 7 * 24 * 3600

# Hosts de imágenes que consideramos confiables para usar sin validar HEAD.
# OpenTripMap devuelve muchas URLs de media.opentripmap.org/catalog que 404 o
# están protegidas; las descartamos y usamos Pexels como fallback.
_HOSTS_IMAGEN_CONFIABLE: set[str] = {
    "images.pexels.com",
    "images.pexels.com",
    "cdn.pixabay.com",
    "upload.wikimedia.org",
    "live.staticflickr.com",
    "cdn.worldota.net",
    "cf.bstatic.com",
    "www.kayak.com",
    "img.kayak.com",
}

# Radio de búsqueda alrededor del centro de la ciudad (metros)
_RADIO_M = 12000
_LIMITE_DEFAULT = 8

# URLs y TTLs para enriquecimiento de POIs (detalle + foto + traducción)
_DETALLE_URL = "https://api.opentripmap.com/0.1/en/places/xid/{xid}"
_PEXELS_URL = "https://api.pexels.com/v1/search"
_TTL_DETALLE = 30 * 24 * 3600      # detalles estables
_TTL_TRADUCCION = 30 * 24 * 3600   # traducciones estables
_TTL_PEXELS = 7 * 24 * 3600        # fotos de stock

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

# Atributos de cada categoría para personalizar según contexto del plan
ATRIBUTOS_CATEGORIA: dict[str, dict] = {
    "Parque de atracciones": {"indoor": False, "familiar": True,  "duracion": "larga",  "precio": "premium"},
    "Museo":                 {"indoor": True,  "familiar": True,  "duracion": "media",  "precio": "economico"},
    "Espectáculo":           {"indoor": True,  "familiar": True,  "duracion": "corta",  "precio": "premium"},
    "Mirador":               {"indoor": False, "familiar": True,  "duracion": "corta",  "precio": "gratis"},
    "Playa":                 {"indoor": False, "familiar": True,  "duracion": "media",  "precio": "gratis"},
    "Templo / Iglesia":      {"indoor": True,  "familiar": True,  "duracion": "corta",  "precio": "gratis"},
    "Parque / Naturaleza":   {"indoor": False, "familiar": True,  "duracion": "media",  "precio": "gratis"},
    "Sitio histórico":       {"indoor": False, "familiar": True,  "duracion": "media",  "precio": "economico"},
    "Atracción":             {"indoor": False, "familiar": True,  "duracion": "media",  "precio": "economico"},
    # Categorías propias del dataset curado
    "Tour guiado":           {"indoor": False, "familiar": True,  "duracion": "media",  "precio": "economico"},
    "Tour gastronómico":     {"indoor": False, "familiar": False, "duracion": "media",  "precio": "premium"},
    "Excursión":             {"indoor": False, "familiar": True,  "duracion": "larga",  "precio": "premium"},
    "Paseo en barca":        {"indoor": False, "familiar": True,  "duracion": "corta",  "precio": "economico"},
    "Paseo en barco":        {"indoor": False, "familiar": True,  "duracion": "corta",  "precio": "economico"},
}

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
    # ─── Colombia / Latinoamérica Norte ───────────────────────────────────
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
    # ─── México y Caribe ──────────────────────────────────────────────────
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
    # ─── Norteamérica ─────────────────────────────────────────────────────
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
    "LAX": [
        ("Paseo de la Fama y Dolby Theatre", "Sitio histórico", "🏰", 0, "Las estrellas de Hollywood y el teatro de los Oscar."),
        ("Santa Mónica Pier", "Parque de atracciones", "🎢", 0, "Muelle icónico con noria, juegos y atardeceres sobre el Pacífico."),
        ("Getty Center", "Museo", "🏛️", 0, "Arte, arquitectura y jardines con vistas panorámicas de Los Ángeles."),
        ("Universal Studios Hollywood", "Parque de atracciones", "🎢", 120, "Parque temático y estudios de cine en plena Hollywood."),
        ("Venice Beach y Muscle Beach", "Playa", "🏖️", 0, "El paseo costero más colorido y alternativo de California."),
    ],
    "SFO": [
        ("Golden Gate Bridge", "Mirador", "🌄", 0, "El puente naranja más fotografiado del mundo, símbolo de San Francisco."),
        ("Alcatraz", "Excursión", "⛴️", 45, "Tour por la famosa prisión en la isla rocosa de la bahía."),
        ("Pier 39 y Fisherman's Wharf", "Atracción", "📍", 0, "Leones marinos, restaurantes y tiendas en el muelle más animado."),
        ("Cable Cars", "Atracción", "📍", 8, "Paseo en los históricos tranvías de cable por las calles empinadas."),
        ("Muir Woods", "Parque / Naturaleza", "🌳", 15, "Bosque de secuoyas gigantes a pocos minutos de la ciudad."),
    ],
    "SEA": [
        ("Pike Place Market", "Atracción", "📍", 0, "Mercado histórico con puestos de pescado, flores y artesanías."),
        ("Space Needle", "Mirador", "🌄", 35, "Vista panorámica de la ciudad, el mar y el Monte Rainier."),
        ("Museo de la Cultura Pop (MoPOP)", "Museo", "🏛️", 30, "Rock, ciencia ficción y cultura popular en un edificio futurista."),
        ("Chihuly Garden and Glass", "Museo", "🏛️", 36, "Esculturas de vidrio soplado junto a la Space Needle."),
        ("Bainbridge Island en ferry", "Excursión", "⛴️", 20, "Paseo en ferry con vistas al skyline y la isla vinícola."),
    ],
    "LAS": [
        ("Paseo por el Strip", "Atracción", "📍", 0, "Los hoteles-casino, fuentes y espectáculos de la avenida principal."),
        ("Show nocturno del Bellagio", "Espectáculo", "🎭", 0, "El famoso espectáculo de fuentes danzantes y luces."),
        ("Gran Cañón del Colorado", "Excursión", "🚌", 120, "Una de las maravillas naturales del mundo, a día completo desde Las Vegas."),
        ("High Roller Observation Wheel", "Mirador", "🌄", 30, "La noria más alta de Norteamérica con vistas nocturnas."),
        ("Fremont Street Experience", "Espectáculo", "🎭", 0, "Toldo de luces LED, música en vivo y ambiente vintage de Las Vegas."),
    ],
    "ATL": [
        ("Georgia Aquarium", "Museo", "🏛️", 45, "Uno de los acuarios más grandes del mundo, con ballenas y tiburones."),
        ("Centennial Olympic Park", "Parque / Naturaleza", "🌳", 0, "Parque heredado de los Juegos Olímpicos de 1996."),
        ("World of Coca-Cola", "Museo", "🏛️", 20, "Historia de la marca y sala de degustación de bebidas de todo el mundo."),
        ("Martin Luther King Jr. National Historic Site", "Sitio histórico", "🏰", 0, "Lugar de nacimiento y museo del líder de derechos civiles."),
        ("Atlanta BeltLine", "Parque / Naturaleza", "🌳", 0, "Sendero urbano con arte, parques y acceso a barrios locales."),
    ],
    "IAH": [
        ("Space Center Houston", "Museo", "🏛️", 35, "Centro espacial con cohetes reales y simuladores de la NASA."),
        ("Museo de Bellas Artes de Houston", "Museo", "🏛️", 20, "Colección de arte europeo, americano y africano."),
        ("Buffalo Bayou Park", "Parque / Naturaleza", "🌳", 0, "Parque lineal con vistas del downtown, ideal para caminar o andar en bici."),
        ("Tour gastronómico por The Heights", "Tour gastronómico", "🍷", 40, "Ruta de cocina internacional y texana en un barrio trendy."),
        ("Mercado japones de Kemah Boardwalk", "Atracción", "📍", 0, "Paseo marítimo con tiendas, restaurantes y vistas de la bahía."),
    ],
    "DFW": [
        ("JFK Memorial y Dealey Plaza", "Sitio histórico", "🏰", 0, "Lugar histórico dedicado al presidente John F. Kennedy."),
        ("Museo de Arte de Dallas", "Museo", "🏛️", 16, "Arte contemporáneo y exposiciones temporales en el Arts District."),
        ("Reunion Tower", "Mirador", "🌄", 20, "Bola geodésica con vistas 360° del skyline de Dallas."),
        ("Six Flags Over Texas", "Parque de atracciones", "🎢", 85, "Parque de montañas rusas y entretenimiento familiar."),
        ("Tour de barbacoa texana", "Tour gastronómico", "🍷", 50, "Ruta por las mejores smokehouses de brisket y ribs de la ciudad."),
    ],
    "BOS": [
        ("Freedom Trail", "Tour guiado", "🚶", 0, "Recorrido de 4 km por los sitios históricos de la Revolución Americana."),
        ("Harvard y MIT", "Sitio histórico", "🏰", 0, "Paseo por los campus históricos de Cambridge."),
        ("Boston Public Garden", "Parque / Naturaleza", "🌳", 0, "Jardín victoriano con los cisnes y barquitos del estanque."),
        ("Museo de Bellas Artes de Boston", "Museo", "🏛️", 27, "Una de las colecciones de arte más importantes de Estados Unidos."),
        ("Paseo en barco por el puerto", "Paseo en barco", "🛥️", 25, "Vistas del puerto, el acuario y el skyline desde el agua."),
    ],
    "IAD": [
        ("National Mall y monumentos", "Sitio histórico", "🏰", 0, "Lincoln Memorial, Washington Monument y Capitolio en un paseo monumental."),
        ("Smithsonian Museums", "Museo", "🏛️", 0, "Museos gratuitos de historia, arte, aire y espacio."),
        ("Casa Blanca", "Sitio histórico", "🏰", 0, "Fachada y jardines de la residencia presidencial de Estados Unidos."),
        ("Georgetown", "Tour guiado", "🚶", 0, "Barrio histórico de calles empedradas, tiendas y restaurantes junto al río."),
        ("Mount Vernon", "Excursión", "🚌", 28, "Hogar y plantación de George Washington, a orillas del río Potomac."),
    ],
    "YYZ": [
        ("CN Tower", "Mirador", "🌄", 30, "Subida a la torre más alta de América del Norte con vistas al lago Ontario."),
        ("Distillery District", "Tour guiado", "🚶", 0, "Barrio peatonal de ladrillo rojo con galerías, cafés y cervecerías."),
        ("Royal Ontario Museum", "Museo", "🏛️", 23, "Arte, cultura mundial y dinosaurios en el centro de Toronto."),
        ("Niagara Falls", "Excursión", "🚌", 90, "Las cataratas más famosas del mundo, a día completo desde Toronto."),
        ("Toronto Islands", "Parque / Naturaleza", "🌳", 10, "Islas frente al skyline, ideales para bicicleta y playas."),
    ],
    "YVR": [
        ("Stanley Park", "Parque / Naturaleza", "🌳", 0, "Parque costero gigante con el Seawall y tótems indígenas."),
        ("Capilano Suspension Bridge", "Parque / Naturaleza", "🌳", 55, "Puente colgante entre bosques de cedros y secuoyas."),
        ("Granville Island", "Atracción", "📍", 0, "Mercado público, artesanías y restaurantes con vista a la bahía."),
        ("Grouse Mountain", "Mirador", "🌄", 50, "Vistas de la ciudad y actividades de montaña todo el año."),
        ("Gastown y Steam Clock", "Sitio histórico", "🏰", 0, "Barrio histórico con el famoso reloj de vapor y calles de adoquines."),
    ],
    # ─── Sudamérica ───────────────────────────────────────────────────────
    "LIM": [
        ("Centro Histórico y Plaza de Armas", "Sitio histórico", "🏰", 0, "El corazón colonial de Lima, Patrimonio de la Humanidad."),
        ("Museo Larco", "Museo", "🏛️", 10, "Arte precolombino en una casona virreinal rodeada de jardines."),
        ("Malecón de Miraflores", "Mirador", "🌄", 0, "Paseo sobre los acantilados con vista al Pacífico y parapentes."),
        ("Circuito Mágico del Agua", "Parque / Naturaleza", "🌳", 4, "Fuentes monumentales con espectáculo de luces por la noche."),
        ("Tour gastronómico por Barranco", "Tour gastronómico", "🍷", 35, "La mejor cocina del mundo en el barrio bohemio de la ciudad."),
    ],
    "SCL": [
        ("Cerro San Cristóbal", "Mirador", "🌄", 0, "Vistas panorámicas de Santiago desde el cerro con teleférico."),
        ("Barrio Bellavista", "Tour gastronómico", "🍷", 30, "Colorido barrio de bares, murales y vida nocturna."),
        ("Museo de la Memoria", "Museo", "🏛️", 0, "Memorial y museo sobre los derechos humanos en Chile."),
        ("Cajón del Maipo", "Excursión", "🚌", 50, "Excursión de día a montañas, ríos y termas en los Andes."),
        ("Plaza de Armas y Catedral", "Sitio histórico", "🏰", 0, "Centro histórico colonial de Santiago."),
    ],
    "EZE": [
        ("Caminito", "Sitio histórico", "🏰", 0, "Calle museo de colores, tango y arte en el barrio de La Boca."),
        ("Recoleta y Cementerio", "Sitio histórico", "🏰", 0, "Barrio elegante con mausoleos históricos y feria de artesanías."),
        ("Teatro Colón", "Espectáculo", "🎭", 25, "Uno de los teatros de ópera más importantes del mundo."),
        ("San Telmo", "Tour gastronómico", "🍷", 35, "Antiguo barrio de ferias, tango y parrillas porteñas."),
        ("Tigre y Delta del Paraná", "Excursión", "🚌", 30, "Paseo en lancha por los canales del delta desde Buenos Aires."),
    ],
    "GIG": [
        ("Cristo Redentor", "Mirador", "🌄", 20, "La estatua icónica del Corcovado con vistas de Río."),
        ("Pan de Azúcar", "Mirador", "🌄", 30, "Subida en teleférico a la montaña más famosa de la ciudad."),
        ("Copacabana e Ipanema", "Playa", "🏖️", 0, "Las playas más icónicas de Brasil para ver y ser visto."),
        ("Jardín Botánico", "Parque / Naturaleza", "🌳", 5, "Bosque de palmeras imperiales y fauna tropical en el corazón de Río."),
        ("Escalera de Selarón", "Sitio histórico", "🏰", 0, "Escaleras de azulejos de colores entre Lapa y Santa Teresa."),
    ],
    "GRU": [
        ("Avenida Paulista", "Atracción", "📍", 0, "Corazón financiero y cultural con museos, cafés y eventos callejeros."),
        ("Mercado Municipal", "Tour gastronómico", "🍷", 25, "Mercado histórico con frutas tropicales y el famoso mortadela sandwich."),
        ("Parque Ibirapuera", "Parque / Naturaleza", "🌳", 0, "El pulmón verde de São Paulo con museos y arquitectura de Niemeyer."),
        ("Beco do Batman", "Museo", "🎨", 0, "Calle de grafitis coloridos en el bohemio barrio de Vila Madalena."),
        ("Museo de Arte de São Paulo (MASP)", "Museo", "🏛️", 10, "Colección de arte europeo en un edificio icónico sobre pilotis."),
    ],
    "UIO": [
        ("Centro Histórico de Quito", "Sitio histórico", "🏰", 0, "La ciudad colonial más alta del mundo, Patrimonio de la Humanidad."),
        ("Basílica del Voto Nacional", "Templo / Iglesia", "⛪", 4, "Impresionante iglesia neogótica con vistas desde sus torres."),
        ("TelefériQo", "Mirador", "🌄", 10, "Subida en teleférico a 4.000 m con vistas de los volcanes."),
        ("Mitad del Mundo", "Atracción", "📍", 5, "Monumento y museo en la línea ecuatorial."),
        ("Mercado de San Francisco", "Tour gastronómico", "🍷", 20, "Sabores quiteños: hornado, empanadas y jugos tropicales."),
    ],
    "PTY": [
        ("Canal de Panamá (Miraflores)", "Museo", "🏛️", 18, "Centro de visitantes con mirador a las esclusas y el paso de barcos."),
        ("Casco Viejo", "Sitio histórico", "🏰", 0, "Centro histórico colonial con cafés, techos y vistas al skyline moderno."),
        ("Cinta Costera", "Parque / Naturaleza", "🌳", 0, "Paseo marítimo de varios kilómetros con vista al océano Pacífico."),
        ("Isla Taboga", "Excursión", "⛴️", 40, "Excursión en ferry a la isla de las flores, playas y senderos."),
        ("Mercado de Mariscos", "Tour gastronómico", "🍷", 25, "Ceviche fresco y cocina de mar con ambiente local."),
    ],
    # ─── Europa ───────────────────────────────────────────────────────────
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
    "AMS": [
        ("Museo Van Gogh", "Museo", "🏛️", 22, "La mayor colección de pinturas y dibujos de Vincent van Gogh."),
        ("Casa de Ana Frank", "Museo", "🏛️", 16, "Museo histórico en la casa donde se escondió la familia Frank."),
        ("Paseo en bote por los canales", "Paseo en barca", "🛶", 18, "Recorrido por los canales patrimoniales del siglo XVII."),
        ("Barrio Jordaan", "Tour guiado", "🚶", 0, "Callejuelas pintorescas, galerías y cafés bohemios."),
        ("Vondelpark", "Parque / Naturaleza", "🌳", 0, "El parque más famoso de Ámsterdam para pasear en bici o picnic."),
    ],
    "BER": [
        ("Muro de Berlín y East Side Gallery", "Sitio histórico", "🏰", 0, "Restos del muro convertidos en galería de arte al aire libre."),
        ("Puerta de Brandeburgo", "Sitio histórico", "🏰", 0, "Símbolo de la reunificación alemana en el corazón de Berlín."),
        ("Museo del Holocausto", "Museo", "🏛️", 0, "Memorial conmemorativo de hormigón al Holocausto judío."),
        ("Museo Pergamo", "Museo", "🏛️", 12, "Artefactos arqueológicos monumentales de la antigüedad."),
        ("Tour gastronómico por Kreuzberg", "Tour gastronómico", "🍷", 35, "Street food internacional y cerveza artesanal en un barrio alternativo."),
    ],
    "MUC": [
        ("Marienplatz y el Ayuntamiento", "Sitio histórico", "🏰", 0, "Plaza central con el carillón y la arquitectura gótica."),
        ("Viktualienmarkt", "Tour gastronómico", "🍷", 20, "Mercado gastronómico con productos bávaros y cervezas."),
        ("Palacio de Nymphenburg", "Sitio histórico", "🏰", 15, "Palacio barroco con jardines, lagos y pabellones."),
        ("Museo BMW", "Museo", "🏛️", 10, "Historia de la marca y exposición de autos y motos icónicas."),
        ("Englischer Garten", "Parque / Naturaleza", "🌳", 0, "Uno de los parques urbanos más grandes del mundo, ideal para surfear en el río."),
    ],
    "LIS": [
        ("Torre de Belém", "Sitio histórico", "🏰", 10, "Monumento manuelino junto al Tajo, símbolo de los Descubrimientos."),
        ("Alfama", "Tour guiado", "🚶", 0, "Barrio más antiguo de Lisboa, de callejuelas, fado y miradores."),
        ("Tranvía 28", "Atracción", "📍", 4, "Paseo en tranvía histórico por los barrios más pintorescos."),
        ("Pastéis de Belém", "Tour gastronómico", "🍷", 5, "Visita a la fábrica original de los pastelitos de nata."),
        ("Sintra", "Excursión", "🚌", 35, "Palacios de cuento a 30 minutos de Lisboa."),
    ],
    "ATH": [
        ("Acrópolis y Partenón", "Sitio histórico", "🏰", 20, "La colina sagrada de Atenas y el templo más famoso de la antigua Grecia."),
        ("Museo de la Acrópolis", "Museo", "🏛️", 10, "Esculturas y tesoros encontrados en la Acrópolis."),
        ("Barrio de Plaka", "Tour guiado", "🚶", 0, "Calles adoquinadas bajo la Acrópolis con tavernas y tiendas."),
        ("Monastiraki", "Atracción", "📍", 0, "Plaza de mercado de pulgas con vistas a la Acrópolis."),
        ("Paseo en barco por el Golfo Sarónico", "Paseo en barco", "🛥️", 40, "Excursión marítima a islas cercanas como Egina o Hydra."),
    ],
    "VIE": [
        ("Palacio de Schönbrunn", "Sitio histórico", "🏰", 20, "Residencia imperial con jardines, zoo y conciertos."),
        ("Centro Histórico y Catedral de San Esteban", "Sitio histórico", "🏰", 0, "Callejuelas imperiales y la catedral gótica más importante."),
        ("Museo de Historia del Arte", "Museo", "🏛️", 18, "Obras maestras de Brueghel, Velázquez y Vermeer."),
        ("Prater y noria gigante", "Parque de atracciones", "🎢", 12, "Parque de diversiones histórico con la icónica Riesenrad."),
        ("Café Central y cafés vienenses", "Tour gastronómico", "🍷", 25, "Tarta Sacher, apfelstrudel y café en templos de la cultura cafetera."),
    ],
    "PRG": [
        ("Puente Carlos", "Sitio histórico", "🏰", 0, "El puente medieval más antiguo de Europa sobre el río Moldava."),
        ("Castillo de Praga", "Sitio histórico", "🏰", 15, "Complejo medieval con catedral, palacios y vistas de la ciudad."),
        ("Plaza de la Ciudad Vieja", "Sitio histórico", "🏰", 0, "Reloj astronómico y casas barrocas de colores."),
        ("Barrio Judío de Josefov", "Tour guiado", "🚶", 0, "Sinagogas históricas y cementerio judío milenario."),
        ("Cata de cerveza checa", "Tour gastronómico", "🍷", 30, "Degustación de pilsner y cervezas artesanales en pubs históricos."),
    ],
    "DUB": [
        ("Temple Bar", "Tour gastronómico", "🍷", 0, "Barrio vibrante de pubs, música en vivo y cerveza Guinness."),
        ("Trinity College y Libro de Kells", "Museo", "🏛️", 18, "Manuscrito iluminado medieval en la universidad más antigua de Irlanda."),
        ("Guinness Storehouse", "Museo", "🏛️", 30, "Experiencia interactiva de la cerveza negra con vista desde el Gravity Bar."),
        ("Phoenix Park", "Parque / Naturaleza", "🌳", 0, "Uno de los parques urbanos cerrados más grandes de Europa, con ciervos."),
        ("Castillo de Dublín", "Sitio histórico", "🏰", 8, "Fortaleza histórica en el centro de la ciudad."),
    ],
    "IST": [
        ("Santa Sofía", "Templo / Iglesia", "⛪", 0, "Antigua basílica, mezquita y hoy museo/mezquita, joya de Bizancio."),
        ("Mezquita Azul", "Templo / Iglesia", "⛪", 0, "Impresionante mezquita otomana con azulejos de İznik."),
        ("Palacio de Topkapi", "Sitio histórico", "🏰", 15, "Residencia de los sultanes con tesoros y vistas al Cuerno de Oro."),
        ("Gran Bazar", "Atracción", "📍", 0, "Uno de los mercados cubiertos más antiguos y grandes del mundo."),
        ("Crucero por el Bósforo", "Paseo en barco", "🛥️", 15, "Paseo entre Europa y Asia con vistas de palacios y mezquitas."),
    ],
    # ─── Asia y Medio Oriente ─────────────────────────────────────────────
    "BKK": [
        ("Gran Palacio y Wat Phra Kaew", "Templo / Iglesia", "⛪", 15, "Complejo real y templo del Buda Esmeralda."),
        ("Wat Arun", "Templo / Iglesia", "⛪", 3, "Templo del Amanecer junto al río Chao Phraya."),
        ("Mercado Chatuchak", "Atracción", "📍", 0, "Mercado de fin de semana con miles de puestos de todo tipo."),
        ("Mercado flotante de Damnoen Saduak", "Excursión", "🚌", 35, "Paseo en barca entre canales llenos de frutas y artesanías."),
        ("Street food en Yaowarat", "Tour gastronómico", "🍷", 15, "El barrio chino de Bangkok: pad thai, mango sticky rice y mariscos."),
    ],
    "NRT": [
        ("Templo Senso-ji", "Templo / Iglesia", "⛪", 0, "Templo budista más antiguo de Tokio, en el barrio de Asakusa."),
        ("Cruce de Shibuya", "Atracción", "📍", 0, "El cruce peatonal más famoso del mundo."),
        ("Torre de Tokio y Zojoji", "Mirador", "🌄", 25, "Vistas de la ciudad desde la torre naranja icónica."),
        ("Mercado Tsukiji Outer", "Tour gastronómico", "🍷", 30, "Sushi fresco, tamago y snacks japoneses en puestos callejeros."),
        ("Shinjuku Gyoen", "Parque / Naturaleza", "🌳", 3, "Jardín imperial con cerezos y vistas del skyline de Shinjuku."),
    ],
    "SIN": [
        ("Marina Bay Sands y Gardens by the Bay", "Parque / Naturaleza", "🌳", 0, "Supertrees, invernaderos futuristas y espectáculo de luces."),
        ("Sentosa y Universal Studios", "Parque de atracciones", "🎢", 80, "Isla de entretenimiento con playas y parque temático."),
        ("Chinatown y Templo de la Reliquia del Diente", "Templo / Iglesia", "⛪", 0, "Barrio histórico chino con templos y mercados."),
        ("Singapore Zoo", "Parque / Naturaleza", "🌳", 40, "Zoológico de fama mundial con recintos abiertos y safaris nocturnos."),
        ("Hawker centers", "Tour gastronómico", "🍷", 10, "Centros de comida callejera: laksa, chili crab y chicken rice."),
    ],
    "HKG": [
        ("Victoria Peak", "Mirador", "🌄", 0, "La vista más icónica del skyline de Hong Kong y el puerto."),
        ("Tian Tan Buddha (Ngong Ping 360)", "Excursión", "🚌", 35, "Buda gigante y templo en la isla de Lantau, accesible en teleférico."),
        ("Mercado de Temple Street", "Atracción", "📍", 0, "Mercado nocturno de ropa, souvenirs y comida local."),
        ("Dim sum en Central", "Tour gastronómico", "🍷", 25, "Tradición de té y dumplings en restaurantes históricos."),
        ("Avenue of Stars y Symphony of Lights", "Espectáculo", "🎭", 0, "Paseo con estrellas del cine y espectáculo de luces nocturno."),
    ],
    "DXB": [
        ("Burj Khalifa", "Mirador", "🌄", 45, "El edificio más alto del mundo y vistas desde el piso 124 o 148."),
        ("Dubai Mall y fuentes", "Atracción", "📍", 0, "Centro comercial gigante con acuario y espectáculo de fuentes."),
        ("Desierto de Dubai (safari)", "Excursión", "🚌", 60, "Dune bashing, campamento beduino y cena bajo las estrellas."),
        ("Barrio Al Fahidi y Dubai Creek", "Sitio histórico", "🏰", 0, "Casas de coral, museos y paseo en abra por la creek histórica."),
        ("Palm Jumeirah y Atlantis", "Atracción", "📍", 0, "La palma artificial con hoteles, playas y acuario."),
    ],
    "DEL": [
        ("Taj Mahal", "Excursión", "🚌", 20, "La joya del arte mogol en Agra, a día completo desde Delhi."),
        ("Fuerte Rojo", "Sitio histórico", "🏰", 8, "Imponente fortaleza de arenisca roja de la dinastía mogol."),
        ("Qutub Minar", "Sitio histórico", "🏰", 10, "El minarete de ladrillo más alto del mundo."),
        ("Humayun's Tomb", "Sitio histórico", "🏰", 5, "Tumba inspiración del Taj Mahal y jardines persas."),
        ("Chandni Chowk y comida callejera", "Tour gastronómico", "🍷", 15, "Mercado caótico de especias, dulces y samosas."),
    ],
    "BOM": [
        ("Gateway of India", "Sitio histórico", "🏰", 0, "Arco monumental frente al mar Arábigo, símbolo colonial de Bombay."),
        ("Marine Drive", "Mirador", "🌄", 0, "Paseo marítimo en forma de C con vistas del atardecer y el Queen's Necklace."),
        ("Dharavi y tour comunitario", "Tour guiado", "🚶", 25, "Recorrido por uno de los barrios más dinámicos y emprendedores de la ciudad."),
        ("Crawford Market", "Atracción", "📍", 0, "Mercado victoriano de frutas, especias y artículos varios."),
        ("Elephanta Caves", "Excursión", "⛴️", 10, "Templos rupestres en una isla del puerto de Bombay."),
    ],
    "ICN": [
        ("Gyeongbokgung Palace", "Sitio histórico", "🏰", 3, "El palacio real más grande de Corea con cambio de guardia."),
        ("Bukchon Hanok Village", "Sitio histórico", "🏰", 0, "Barrio tradicional de casas de madera entre palacios."),
        ("N Seoul Tower", "Mirador", "🌄", 15, "Vistas panorámicas de Seúl desde la torre en el monte Namsan."),
        ("Myeongdong", "Tour gastronómico", "🍷", 0, "Distrito de compras y comida callejera: tteokbokki, hotteok y cosmética."),
        ("DMZ Tour", "Excursión", "🚌", 65, "Excursión a la zona desmilitarizada entre Corea del Norte y del Sur."),
    ],
    # ─── Oceanía y África ─────────────────────────────────────────────────
    "SYD": [
        ("Ópera de Sídney", "Espectáculo", "🎭", 30, "Icono arquitectónico mundial con recorridos y espectáculos."),
        ("Puente del Puerto de Sídney", "Mirador", "🌄", 25, "Escalada o paseo con vistas de la bahía y la ópera."),
        ("Bondi Beach", "Playa", "🏖️", 0, "La playa más famosa de Australia para surfistas y paseantes."),
        ("Royal Botanic Garden", "Parque / Naturaleza", "🌳", 0, "Jardines frente al puerto con vistas a la ópera."),
        ("Blue Mountains", "Excursión", "🚌", 70, "Día completo a acantilados, eucaliptos y las Three Sisters."),
    ],
    "MEL": [
        ("Hosier Lane", "Museo", "🎨", 0, "Calle emblemática de arte urbano en el centro de Melbourne."),
        ("Queen Victoria Market", "Atracción", "📍", 0, "Mercado histórico de alimentos, ropa y souvenirs."),
        ("Great Ocean Road", "Excursión", "🚌", 120, "Una de las carreteras costeras más espectaculares del mundo."),
        ("Royal Botanic Gardens", "Parque / Naturaleza", "🌳", 0, "Jardines extensos junto al río Yarra."),
        ("Tour de cafés y brunch", "Tour gastronómico", "🍷", 30, "Cultura cafetera de Melbourne: flat white y avo toast."),
    ],
    "AKL": [
        ("Sky Tower", "Mirador", "🌄", 25, "Vistas de Auckland y los volcanes desde la torre más alta del hemisferio sur."),
        ("Waiheke Island", "Excursión", "⛴️", 45, "Isla de viñedos, playas y arte a 40 minutos en ferry."),
        ("Waitomo Glowworm Caves", "Excursión", "🚌", 90, "Cavernas con gusanos luminiscentes en paseo en bote."),
        ("Mount Eden", "Mirador", "🌄", 0, "Cráter volcánico con vista panorámica del centro de Auckland."),
        ("Viaduct Harbour", "Paseo en barco", "🛥️", 30, "Puerto moderno con restaurantes, yates y paseos marítimos."),
    ],
    "CPT": [
        ("Table Mountain", "Mirador", "🌄", 25, "Subida en teleférico a la montaña plana con vistas de Ciudad del Cabo."),
        ("Cabo de Buena Esperanza", "Excursión", "🚌", 80, "Reserva natural y punto más suroccidental de África."),
        ("V&A Waterfront", "Atracción", "📍", 0, "Puerto histórico con tiendas, restaurantes y vistas de Table Mountain."),
        ("Boulders Beach", "Playa", "🏖️", 10, "Playa con colonia de pingüinos africanos."),
        ("Kirstenbosch Gardens", "Parque / Naturaleza", "🌳", 8, "Jardín botánico en las laderas de Table Mountain."),
    ],
    "CAI": [
        ("Pirámides de Giza", "Excursión", "🚌", 30, "Las últimas maravillas de la antigüedad y la Esfinge."),
        ("Museo Egipcio", "Museo", "🏛️", 12, "Tesoros faraónicos, incluida la máscara de Tutankamón."),
        ("Mercado de Jan el-Jalili", "Atracción", "📍", 0, "Mercado histórico de especias, perfumes y artesanías."),
        ("Mezquita de Mohamed Ali", "Templo / Iglesia", "⛪", 5, "Ciudadela otomana con vistas de El Cairo."),
        ("Crucero por el Nilo", "Paseo en barco", "🛥️", 25, "Cena y espectáculo navegando por el río Nilo."),
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
    # Latinoamérica
    "bogota": "BOG", "medellin": "MDE", "cartagena": "CTG",
    "ciudad de mexico": "MEX", "mexico city": "MEX", "cancun": "CUN",
    "miami": "MIA", "orlando": "MCO",
    "nueva york": "JFK", "new york": "JFK",
    "lima": "LIM",
    "santiago": "SCL", "santiago de chile": "SCL",
    "buenos aires": "EZE",
    "rio de janeiro": "GIG",
    "sao paulo": "GRU", "saopaulo": "GRU",
    "quito": "UIO",
    "panama": "PTY", "ciudad de panama": "PTY",
    # Norteamérica
    "los angeles": "LAX", "san francisco": "SFO", "seattle": "SEA",
    "las vegas": "LAS",
    "atlanta": "ATL", "houston": "IAH", "dallas": "DFW",
    "boston": "BOS", "washington": "IAD", "washington dc": "IAD",
    "toronto": "YYZ", "vancouver": "YVR",
    # Europa
    "madrid": "MAD", "barcelona": "BCN",
    "paris": "CDG", "paris": "CDG",
    "roma": "FCO", "rome": "FCO",
    "londres": "LHR", "london": "LHR",
    "amsterdam": "AMS",
    "berlin": "BER",
    "munich": "MUC", "munchen": "MUC",
    "lisboa": "LIS", "lisbon": "LIS",
    "atenas": "ATH", "athens": "ATH",
    "viena": "VIE", "vienna": "VIE",
    "praga": "PRG", "prague": "PRG",
    "dublin": "DUB",
    "estambul": "IST", "istanbul": "IST",
    # Asia / Medio Oriente
    "bangkok": "BKK",
    "tokio": "NRT", "tokyo": "NRT",
    "singapur": "SIN", "singapore": "SIN",
    "hong kong": "HKG",
    "dubai": "DXB",
    "delhi": "DEL", "nueva delhi": "DEL", "new delhi": "DEL",
    "mumbai": "BOM", "bombay": "BOM",
    "seul": "ICN", "seoul": "ICN",
    # Oceanía / África
    "sidney": "SYD", "sydney": "SYD",
    "melbourne": "MEL",
    "auckland": "AKL",
    "ciudad del cabo": "CPT", "cape town": "CPT",
    "el cairo": "CAI", "cairo": "CAI",
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


def _calcular_noches(fecha_salida: str, fecha_regreso: str) -> int:
    """Calcula noches entre dos fechas en formato YYYY-MM-DD."""
    try:
        salida = datetime.strptime(fecha_salida, "%Y-%m-%d")
        regreso = datetime.strptime(fecha_regreso, "%Y-%m-%d")
        noches = (regreso - salida).days
        return max(noches, 0)
    except (ValueError, TypeError):
        return 0


def _bucket_lluvia(clima: dict | None) -> str:
    """
    Devuelve un bucket discretizado según la probabilidad de lluvia promedio
    del pronóstico/típico recibido.
    """
    if not clima or not isinstance(clima, dict):
        return "sin"
    dias = clima.get("dias") or clima.get("dias", [])
    if not dias:
        return "sin"
    try:
        probs = [d.get("prob_lluvia", 0) for d in dias if d.get("prob_lluvia") is not None]
        if not probs:
            return "sin"
        promedio = mean(probs)
    except Exception:
        return "sin"
    if promedio >= 60:
        return "alta"
    if promedio >= 25:
        return "media"
    return "baja"


def _bucket_pasajeros(pasajeros: int) -> str:
    """Solo / pareja / grupo, según número de pasajeros."""
    if pasajeros >= 4:
        return "grupo"
    if pasajeros >= 2:
        return "pareja"
    return "solo"


def _score_actividad(
    act: dict,
    tier: str,
    lluvia_bucket: str,
    pax_bucket: str,
    noches: int,
) -> float:
    """
    Score de relevancia contextual. Valores altos suben en la lista.
    El ordenamiento es estable: en empate se mantiene el orden original.
    """
    attrs = ATRIBUTOS_CATEGORIA.get(act.get("categoria", ""), {})
    indoor = attrs.get("indoor", False)
    familiar = attrs.get("familiar", True)
    duracion = attrs.get("duracion", "media")
    precio_tipo = attrs.get("precio", "economico")
    gratis = act.get("gratis", False)

    score = 0.0

    # --- Tier ---
    tier = (tier or "estandar").lower()
    if tier == "economico":
        if gratis:
            score += 2.5
        elif precio_tipo == "economico":
            score += 1.0
        elif precio_tipo == "premium":
            score -= 1.5
    elif tier == "premium":
        if precio_tipo == "premium":
            score += 2.0
        elif precio_tipo == "economico":
            score += 0.5
        elif gratis:
            score -= 1.0
    else:  # estandar
        if gratis:
            score += 1.0
        elif precio_tipo == "economico":
            score += 0.5
        elif precio_tipo == "premium":
            score -= 0.5

    # --- Clima ---
    if lluvia_bucket == "alta":
        score += 2.5 if indoor else -2.0
    elif lluvia_bucket == "media":
        score += 0.8 if indoor else -0.5
    elif lluvia_bucket == "baja":
        score += 1.0 if not indoor else -0.3

    # --- Pasajeros ---
    if pax_bucket == "grupo":
        score += 1.5 if familiar else -0.8
    elif pax_bucket == "pareja":
        score += 0.6 if not familiar else 0.2

    # --- Duración del viaje ---
    if noches <= 2:
        if duracion == "larga":
            score -= 3.0
        elif duracion == "corta":
            score += 0.5
    elif noches >= 5:
        if duracion == "larga":
            score += 1.5
        elif duracion == "media":
            score += 0.5

    return score


def _boost_por_contexto(
    actividades: list[dict],
    tier: str,
    clima: dict | None,
    pasajeros: int,
    fecha_salida: str,
    fecha_regreso: str,
) -> list[dict]:
    """
    Reordena (y descarta excursiones en viajes muy cortos) según el contexto
    del plan. No muta los dicts originales.
    """
    if not actividades:
        return []

    lluvia_bucket = _bucket_lluvia(clima)
    pax_bucket = _bucket_pasajeros(pasajeros)
    noches = _calcular_noches(fecha_salida, fecha_regreso)

    def _key(act: dict) -> tuple:
        score = _score_actividad(act, tier, lluvia_bucket, pax_bucket, noches)
        precio = act.get("precio_estimado", 0) or 0
        # En empate: gratis primero, luego precio ascendente, luego nombre
        return (-score, 0 if act.get("gratis") else 1, precio, act.get("nombre", ""))

    return sorted(actividades, key=_key)


def _tiene_curado(iata: str | None, ciudad: str) -> bool:
    """Indica si existe un dataset curado para este destino."""
    key = (iata or "").upper()
    if key and key in ACTIVIDADES_CURADAS:
        return True
    key = _IATA_POR_CIUDAD.get(_normalizar(ciudad), "")
    return key in ACTIVIDADES_CURADAS


def _fusionar_actividades(
    curadas: list[dict],
    reales: list[dict],
    limite: int,
) -> list[dict]:
    """
    Combina actividades curadas (prioridad) con actividades reales de OpenTripMap,
    evitando duplicados por nombre. Mantiene el orden de cada lista.
    """
    vistos: set[str] = set()
    resultado: list[dict] = []

    for act in curadas:
        nombre = act.get("nombre", "").strip().lower()
        if not nombre or nombre in vistos:
            continue
        vistos.add(nombre)
        resultado.append(act)
        if len(resultado) >= limite:
            return resultado

    for act in reales:
        nombre = act.get("nombre", "").strip().lower()
        if not nombre or nombre in vistos:
            continue
        vistos.add(nombre)
        resultado.append(act)
        if len(resultado) >= limite:
            return resultado

    return resultado


def _actividades_curadas(
    ciudad: str,
    iata: str | None,
    limite: int,
    *,
    tier: str = "estandar",
    fecha_salida: str = "",
    fecha_regreso: str = "",
    clima: dict | None = None,
    pasajeros: int = 1,
    fotos_pexels: list[str] | None = None,
) -> dict:
    """Selección curada local: por IATA, por nombre de ciudad o '_default'."""
    key = (iata or "").upper()
    entradas = ACTIVIDADES_CURADAS.get(key)
    if not entradas:
        key = _IATA_POR_CIUDAD.get(_normalizar(ciudad), "")
        entradas = ACTIVIDADES_CURADAS.get(key, ACTIVIDADES_CURADAS["_default"])

    actividades: list[dict] = []
    fotos = fotos_pexels or []
    for i, (nombre, categoria, icono, precio, descripcion) in enumerate(entradas):
        act = _armar_actividad(nombre, categoria, icono, precio, descripcion, ciudad, fuente="curado")
        act["foto_url"] = fotos[i % len(fotos)] if fotos else ""
        actividades.append(act)

    actividades = _boost_por_contexto(
        actividades, tier=tier, clima=clima,
        pasajeros=pasajeros, fecha_salida=fecha_salida, fecha_regreso=fecha_regreso,
    )[:limite]
    return {
        "ciudad":      ciudad,
        "actividades": actividades,
        "precision":   "estimada",
        "aviso":       f"Selección curada por RushTrip. {_AVISO_PRECIOS}",
    }


async def _fotos_pexels(ciudad: str, limite: int = 12) -> list[str]:
    """
    Devuelve URLs de fotos de actividades/turismo para la ciudad usando Pexels.
    Se cachea por ciudad; sin API key devuelve lista vacía.
    """
    if not settings.pexels_api_key:
        return []

    cache_key = f"pexels_activities:{ciudad.lower().strip()}"
    cached = cache_get(cache_key)
    if cached and isinstance(cached, list):
        return cached

    try:
        resp = await request_with_retry(
            "GET", _PEXELS_URL,
            provider="pexels",
            max_retries=1,
            headers={"Authorization": settings.pexels_api_key},
            params={
                "query": f"{ciudad} tourist attraction",
                "per_page": limite,
                "orientation": "landscape",
            },
        )
        data = resp.json()
        fotos = [p.get("src", {}).get("medium", "") for p in data.get("photos", [])]
        fotos = [f for f in fotos if f]
        if fotos:
            cache_set(cache_key, fotos, provider="pexels", ttl_seconds=_TTL_PEXELS)
        return fotos
    except Exception as e:
        logger.warning(f"No se pudieron cargar fotos de Pexels para '{ciudad}': {e}")
        return []


_STOP_WORDS_EN: set[str] = {
    "the", "and", "of", "in", "is", "are", "was", "were", "with", "to",
    "from", "by", "on", "at", "for", "a", "an", "this", "that", "it",
    "you", "he", "she", "we", "they", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should",
}

_STOP_WORDS_ES: set[str] = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "de",
    "del", "que", "con", "por", "para", "es", "son", "en", "al", "su",
    "sus", "lo", "le", "se", "me", "te", "nos", "más", "como", "pero",
    "sino", "si", "no", "sí", "ya", "todo", "todos", "toda", "todas",
}

_MARCAS_ES: set[str] = {"á", "é", "í", "ó", "ú", "ü", "ñ", "¿", "¡"}


def _parece_espanol(texto: str) -> bool:
    """
    Heurística robusta para decidir si un texto está en español.

    Un texto en inglés que mencione nombres propios acentuados (p.ej.
    "museum in Málaga") daba falsos positivos con la heurística anterior.
    Ahora exigimos señales más fuertes:
      - densidad de marcas españolas (>= 2), O
      - presencia de stop-words españolas, O
      - ausencia total de stop-words inglesas con al menos 1 marca española.
    Si aparecen stop-words inglesas frecuentes, descartamos que sea español.
    """
    if not texto:
        return False

    lowered = texto.lower()
    palabras = set(re.findall(r"\b[a-zñáéíóúü]+\b", lowered))

    # Si hay stop-words inglesas claras, no es español (evita falsos positivos
    # como "The museum is one of the most visited in Málaga").
    if palabras.intersection(_STOP_WORDS_EN):
        return False

    marcas = sum(1 for c in lowered if c in _MARCAS_ES)
    if marcas >= 2:
        return True

    if palabras.intersection(_STOP_WORDS_ES):
        return True

    # Caso sin stop-words identificables pero con al menos una marca: damos el
    # beneficio de la duda (nombres propios o frases muy cortas).
    return marcas >= 1


def _cache_key_traduccion(textos: list[str]) -> str:
    """Hash determinista de la lista de textos; estable entre reinicios."""
    blob = "\x00".join(t.strip() for t in textos)
    digest = hashlib.sha1(blob.encode("utf-8")).hexdigest()
    return f"deepl:v2:{digest}"


async def _traducir_descripciones(
    textos: list[str],
    categorias: list[str] | None = None,
    ciudades: list[str] | None = None,
) -> list[str]:
    """
    Traduce una lista de textos al español vía DeepL API Free.
    Si no hay key, la API falla o no hay textos, devuelve los originales.
    Se cachea la traducción completa como un solo bloque.

    Si DeepL falla, los textos que no parezcan español se reemplazan por una
    plantilla en español (usando la categoría y ciudad si se proveen) para
    evitar mostrar italiano, griego, etc.
    """
    if not textos:
        return textos

    categorias = categorias or ["Atracción"] * len(textos)
    ciudades = ciudades or [""] * len(textos)

    # Sin key de DeepL: cualquier texto no español se pisa por plantilla española.
    if not settings.deepl_api_key:
        return [
            t if _parece_espanol(t) else _descripcion_por_categoria(categorias[i], ciudades[i])
            for i, t in enumerate(textos)
        ]

    # Normalizar: ignorar vacíos y plantillas (que ya están en español)
    indices_a_traducir = [
        i for i, t in enumerate(textos)
        if t and len(t.strip()) > 5 and not _parece_espanol(t)
    ]
    if not indices_a_traducir:
        return textos

    cache_key = _cache_key_traduccion(textos)
    cached = cache_get(cache_key)
    if cached and isinstance(cached, list) and len(cached) == len(textos):
        return cached

    try:
        payload = {
            "auth_key": settings.deepl_api_key,
            "target_lang": "ES",
            # No forzamos source_lang: DeepL auto-detecta (es, en, it, el, etc.).
        }
        for i in indices_a_traducir:
            payload.setdefault("text", []).append(textos[i])

        resp = await request_with_retry(
            "POST", settings.deepl_api_url,
            provider="deepl",
            max_retries=1,
            data=payload,
        )
        data = resp.json()
        # DeepL Free devuelve {'translations': [...]}; algunos proxies/tests
        # pueden devolver la lista directamente.
        if isinstance(data, list):
            traducciones = [t.get("text", "") if isinstance(t, dict) else str(t) for t in data]
        else:
            traducciones = [t.get("text", "") for t in data.get("translations", [])]

        resultado = list(textos)
        for idx, trad in zip(indices_a_traducir, traducciones):
            if trad:
                resultado[idx] = trad

        cache_set(cache_key, resultado, provider="deepl", ttl_seconds=_TTL_TRADUCCION)
        return resultado
    except Exception as e:
        logger.warning(f"DeepL no pudo traducir descripciones: {e}")
        return [
            t if _parece_espanol(t) else _descripcion_por_categoria(categorias[i], ciudades[i])
            for i, t in enumerate(textos)
        ]


def _extraer_descripcion_poi(data: dict) -> str:
    """Extrae la mejor descripción disponible del detalle de OpenTripMap."""
    wiki = data.get("wikipedia_extracts") or {}
    descripcion = (wiki.get("text") or "").strip()
    if not descripcion:
        info = data.get("info") or {}
        descripcion = (info.get("descr") or "").strip()
    return descripcion


async def _detalle_poi_opentripmap(xid: str, language: str) -> dict:
    """Consulta /places/xid con un idioma específico."""
    url = _DETALLE_URL.format(xid=xid)
    resp = await request_with_retry(
        "GET", url,
        provider="opentripmap",
        max_retries=1,
        params={
            "apikey": settings.opentripmap_api_key,
            "language": language,
        },
    )
    return resp.json()


_EXTENSIONES_IMAGEN = re.compile(r"\.(jpg|jpeg|png|webp|gif|bmp)(\?.*)?$", re.IGNORECASE)


def _url_imagen_confiable(url: str) -> str:
    """
    Devuelve la URL si consideramos que puede cargarse como imagen; si no, vacío.

    Descartamos explícitamente las URLs del catálogo de OpenTripMap, que suelen
    estar rotas o protegidas. El resto se acepta si termina en extensión de imagen
    conocida o proviene de un host en la lista blanca.
    """
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return ""

    lowered = url.lower()
    if "opentripmap.org/catalog" in lowered or "otmap.org/catalog" in lowered:
        return ""

    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return ""
    host = host.lower().lstrip("www.")

    if _EXTENSIONES_IMAGEN.search(url):
        return url

    if any(
        host == confiable or host.endswith("." + confiable.split(".", 1)[-1])
        for confiable in _HOSTS_IMAGEN_CONFIABLE
    ):
        return url

    return ""


async def _enriquecer_poi_opentripmap(xid: str, ciudad: str) -> dict:
    """
    Consulta el detalle de un POI por su XID y devuelve un dict con
    descripción (preferentemente en español) y foto_url.

    Estrategia de idioma:
      1. Pedir language=es (extracto de Wikipedia en español si existe).
      2. Si no trae descripción, reintentar language=en.
      3. Si aún así llega un texto que no parece español, _traducir_descripciones
         se encargará de traducirlo o reemplazarlo por plantilla en español.

    La foto se valida contra hosts confiables para evitar URLs rotas de
    media.opentripmap.org/catalog.
    """
    if not xid:
        return {"descripcion": "", "foto_url": ""}

    cache_key = f"opentripmap:xid:{xid}"
    cached = cache_get(cache_key)
    if cached and isinstance(cached, dict):
        return cached

    try:
        # 1) Intento en español
        data = await _detalle_poi_opentripmap(xid, language="es")
        descripcion = _extraer_descripcion_poi(data)

        # 2) Fallback a inglés si no hubo descripción
        if not descripcion:
            data = await _detalle_poi_opentripmap(xid, language="en")
            descripcion = _extraer_descripcion_poi(data)

        foto_url = _url_imagen_confiable(
            data.get("image") or data.get("preview", {}).get("source") or ""
        )

        resultado = {"descripcion": descripcion, "foto_url": foto_url or ""}
        cache_set(cache_key, resultado, provider="opentripmap", ttl_seconds=_TTL_DETALLE)
        return resultado
    except Exception as e:
        logger.warning(f"No se pudo enriquecer POI {xid} de OpenTripMap: {e}")
        return {"descripcion": "", "foto_url": ""}


async def _consultar_opentripmap(
    lat: float,
    lon: float,
    ciudad: str,
    limite: int,
    *,
    tier: str = "estandar",
    fecha_salida: str = "",
    fecha_regreso: str = "",
    clima: dict | None = None,
    pasajeros: int = 1,
    fotos_pexels: list[str] | None = None,
) -> list[dict]:
    """
    Mejores POIs turísticos alrededor del centro de la ciudad, ordenados por
    relevancia ('rate' de OpenTripMap). Lanza ExternalAPIError si la API falla.
    Enriquece cada POI con detalle (/places/xid), foto propia o Pexels, y
    traduce la descripción al español vía DeepL si hay key configurada.
    El boost por contexto se aplica sobre la lista final.
    """
    resp = await request_with_retry(
        "GET", _RADIUS_URL,
        provider="opentripmap",
        max_retries=1,
        params={
            "radius": _RADIO_M,
            "lon":    lon,
            "lat":    lat,
            "kinds":  (
                "interesting_places,amusements,museums,art_galleries,"
                "historic,historic_architecture,castles,fortifications,"
                "monuments_and_memorials,archaeology,religion,churches,"
                "cathedrals,view_points,towers,gardens_and_parks,natural,"
                "beaches,theatres_and_entertainments,cinemas"
            ),
            "rate":   2,
            "limit":  limite * 4,
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

    # 1) POIs base ordenados por relevancia, sin duplicados
    pois_base = []
    vistos: set[str] = set()
    for poi in sorted(resp.json(), key=lambda p: p.get("rate", 0), reverse=True):
        nombre = (poi.get("name") or "").strip()
        if not nombre or nombre.lower() in vistos:
            continue
        vistos.add(nombre.lower())
        pois_base.append(poi)
        if len(pois_base) >= limite:
            break

    if not pois_base:
        return []

    # 2) Enriquecer detalles en paralelo
    detalles = await asyncio.gather(*(
        _enriquecer_poi_opentripmap(poi.get("xid", ""), ciudad)
        for poi in pois_base
    ))

    # 3) Traducir descripciones reales al español (si hay DeepL key)
    textos_originales = [d.get("descripcion", "") for d in detalles]
    categorias = [_clasificar_kinds(poi.get("kinds", ""))[0] for poi in pois_base]
    textos_traducidos = await _traducir_descripciones(
        textos_originales, categorias=categorias, ciudades=[ciudad] * len(pois_base)
    )

    # 4) Fotos de fallback (proporcionadas por el caller para evitar doble llamada)
    fotos_pexels = fotos_pexels or []

    # 5) Armar actividades con descripción enriquecida + foto
    actividades: list[dict] = []
    for i, poi in enumerate(pois_base):
        nombre = (poi.get("name") or "").strip()
        categoria, icono, precio = _clasificar_kinds(poi.get("kinds", ""))
        detalle = detalles[i]
        descripcion_raw = textos_traducidos[i] or detalle.get("descripcion", "")

        # Si no hay descripción real o es sospechosamente corta, usar plantilla en español
        if not descripcion_raw or len(descripcion_raw) < 10:
            descripcion = _descripcion_por_categoria(categoria, ciudad)
        else:
            descripcion = descripcion_raw

        foto_url = detalle.get("foto_url", "")
        if not foto_url and fotos_pexels:
            foto_url = fotos_pexels[i % len(fotos_pexels)]

        act = _armar_actividad(
            nombre, categoria, icono, precio, descripcion, ciudad, fuente="opentripmap",
        )
        act["foto_url"] = foto_url
        actividades.append(act)

    # 6) Boost contextual
    actividades = _boost_por_contexto(
        actividades, tier=tier, clima=clima,
        pasajeros=pasajeros, fecha_salida=fecha_salida, fecha_regreso=fecha_regreso,
    )
    return actividades


async def obtener_actividades(
    ciudad: str,
    iata: str | None = None,
    limite: int = _LIMITE_DEFAULT,
    *,
    tier: str = "estandar",
    fecha_salida: str = "",
    fecha_regreso: str = "",
    clima: dict | None = None,
    pasajeros: int = 1,
    incluir_vehiculo: bool = False,
) -> dict:
    """
    Mejores actividades del destino.

    Cascada: cache → OpenTripMap (si hay key) + curado local → cache stale → curado.
    Siempre devuelve un dict con 'ciudad', 'actividades', 'precision' y 'aviso' —
    nunca lanza excepción ni devuelve la lista vacía.

    El resultado se personaliza según tier, clima, pasajeros y duración del viaje.
    """
    ciudad_limpia = ciudad.strip()
    lluvia_bucket = _bucket_lluvia(clima)
    pax_bucket = _bucket_pasajeros(pasajeros)
    # Cache key separada por contexto discretizado para no mezclar recomendaciones
    # de distintos perfiles de viaje.
    cache_key = (
        f"actividades:{ciudad_limpia.lower()}:{limite}:"
        f"{tier.lower()}:{lluvia_bucket}:{pax_bucket}"
    )

    cached = cache_get(cache_key)
    if cached:
        return cached

    # Fotos de stock una sola vez; se pasan a curado y a OpenTripMap para evitar
    # llamadas dobles y mantener consistencia visual.
    fotos_pexels = await _fotos_pexels(ciudad_limpia, limite=limite)

    try:
        if settings.opentripmap_api_key:
            coords = await resolver_coords(ciudad_limpia, iata=iata)
            if coords:
                lat, lon = coords
                try:
                    actividades_reales = await _consultar_opentripmap(
                        lat, lon, ciudad_limpia, limite,
                        tier=tier, fecha_salida=fecha_salida, fecha_regreso=fecha_regreso,
                        clima=clima, pasajeros=pasajeros,
                        fotos_pexels=fotos_pexels,
                    )
                    if actividades_reales:
                        # Si tenemos curado local para este destino, fusionamos:
                        # curado primero (calidad garantizada en español), reales
                        # para rellenar sin duplicar.
                        if _tiene_curado(iata, ciudad_limpia):
                            curado = _actividades_curadas(
                                ciudad_limpia, iata, limite,
                                tier=tier, fecha_salida=fecha_salida,
                                fecha_regreso=fecha_regreso, clima=clima,
                                pasajeros=pasajeros, fotos_pexels=fotos_pexels,
                            )["actividades"]
                            actividades = _fusionar_actividades(
                                curado, actividades_reales, limite
                            )
                        else:
                            actividades = actividades_reales[:limite]

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

    return _actividades_curadas(
        ciudad_limpia, iata, limite,
        tier=tier, fecha_salida=fecha_salida, fecha_regreso=fecha_regreso,
        clima=clima, pasajeros=pasajeros, fotos_pexels=fotos_pexels,
    )
