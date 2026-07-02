# tests/test_hotels.py
# Tests de la lógica de hoteles: links de reserva, precios de referencia,
# preservación de imágenes reales y detalle on-demand.

from core.config import settings
import services.hotels as hotels


# ── Links de reserva ──────────────────────────────────────────────────────

def test_link_reserva_directo_sin_afiliado(monkeypatch):
    monkeypatch.setattr(settings, "travelpayouts_hotel_link", "")
    link = hotels._link_reserva_tp("Hotel X", "Madrid", "2026-10-10", "2026-10-14", 2)
    assert link.startswith("https://www.booking.com/searchresults.html")
    assert "tp.media" not in link
    assert "checkin=2026-10-10" in link
    assert "group_adults=2" in link


def test_link_reserva_envuelve_con_prefijo(monkeypatch):
    monkeypatch.setattr(
        settings, "travelpayouts_hotel_link",
        "https://tp.media/r?marker=723238&trs=1&p=8310",
    )
    link = hotels._link_reserva_tp("Only YOU", "Madrid", "2026-10-10", "2026-10-14", 2)
    assert link.startswith("https://tp.media/r?marker=723238")
    assert "&u=https%3A%2F%2Fwww.booking.com" in link


# ── Cálculos de referencia ────────────────────────────────────────────────

def test_calcular_noches():
    assert hotels._calcular_noches("2026-10-10", "2026-10-14") == 4
    assert hotels._calcular_noches("2026-10-10", "2026-10-10") == 1  # mínimo 1
    assert hotels._calcular_noches("2026-10-10", "2026-10-11") == 1


def test_precio_referencia():
    assert hotels._precio_referencia("MAD") == hotels.PRECIO_REFERENCIA_HOTEL["MAD"]
    assert hotels._precio_referencia("mad") == hotels.PRECIO_REFERENCIA_HOTEL["MAD"]
    assert hotels._precio_referencia("ZZZ") == hotels.PRECIO_REFERENCIA_HOTEL["_default"]


def test_generar_hoteles_afiliados(monkeypatch):
    monkeypatch.setattr(settings, "travelpayouts_hotel_link", "")
    hs = hotels._generar_hoteles_afiliados("Madrid", "2026-10-10", "2026-10-14", 2, 4, 90)
    assert len(hs) == 4
    assert all(h["tipo"] == "estimado" for h in hs)
    assert all(h["link_reserva"].startswith("https://www.booking.com") for h in hs)
    assert all(h["precio_total"] > 0 for h in hs)


# ── Preservación de imágenes reales (el bug que arreglamos) ───────────────

async def test_enriquecer_preserva_imagen_real(monkeypatch):
    monkeypatch.setattr(settings, "pexels_api_key", "fake-key")
    hotels._PEXELS_CACHE.set("pexels_madrid", ["http://pexels/1.jpg", "http://pexels/2.jpg"])
    hoteles = [
        {"nombre": "Real Hotel", "tipo": "real",
         "foto_url": "http://cdn.worldota/real.jpg", "fotos_urls": ["http://cdn.worldota/real.jpg"]},
        {"nombre": "Estimado", "tipo": "estimado", "foto_url": "", "fotos_urls": []},
    ]
    out = await hotels._enriquecer_con_fotos("Madrid", hoteles)
    # El hotel real conserva SU foto (no la sobreescribe Pexels)
    assert out[0]["foto_url"] == "http://cdn.worldota/real.jpg"
    # El estimado recibe la foto de ciudad de Pexels
    assert out[1]["foto_url"] == "http://pexels/1.jpg"


# ── Validación de país de Hotels.nl (bug ZAG → hoteles de Ámsterdam) ─────

def _mock_ciudad(monkeypatch, nombre, pais_codigo, codigo):
    async def fake_aeropuerto(texto):
        return [{"nombre": nombre, "pais": "", "pais_codigo": pais_codigo, "codigo": codigo}]
    monkeypatch.setattr(hotels, "buscar_aeropuerto", fake_aeropuerto)


def _hotel_nl(nombre, ciudad, pais, precio=100.0):
    return {
        "nombre": nombre, "ciudad": ciudad, "pais": pais, "estrellas": 4,
        "rating": 8.0, "reviewScoreWord": "Muy bien", "reviewCount": 100,
        "precio_noche": precio / 4, "precio_total": precio, "noches": 4,
        "adultos": 2, "moneda": "USD", "foto_url": "http://img", "fotos_urls": [],
        "amenities": [], "tipo": "real",
    }


async def test_buscar_hoteles_descarta_pais_incorrecto(monkeypatch):
    # Hotels.nl no reconoce la ubicación y devuelve hoteles de Ámsterdam:
    # deben descartarse y caer al fallback de precios de referencia
    _mock_ciudad(monkeypatch, "Zagreb", "HR", "ZAG")

    async def fake_nl(**kwargs):
        return [_hotel_nl("Hotel de Munck", "Amsterdam", "NL")]

    monkeypatch.setattr(hotels, "buscar_hoteles_nl", fake_nl)
    monkeypatch.setattr(settings, "hotelsnl_api_key", "x")
    monkeypatch.setattr(settings, "pexels_api_key", "")

    res = await hotels.buscar_hoteles("Zagreb", "2026-09-10", "2026-09-14")

    assert res["precision"] == "estimada"
    assert all(h["tipo"] == "estimado" for h in res["hoteles"])
    assert all("Amsterdam" not in h["nombre"] for h in res["hoteles"])
    assert res["ciudad"] == "Zagreb"


async def test_buscar_hoteles_filtra_solo_pais_esperado(monkeypatch):
    # Si hay mezcla, se conservan solo los hoteles del país del destino
    _mock_ciudad(monkeypatch, "Zagreb", "HR", "ZAG")

    async def fake_nl(**kwargs):
        return [
            _hotel_nl("Art Hotel Like", "Zagreb", "HR"),
            _hotel_nl("Hotel de Munck", "Amsterdam", "NL"),
        ]

    monkeypatch.setattr(hotels, "buscar_hoteles_nl", fake_nl)
    monkeypatch.setattr(settings, "hotelsnl_api_key", "x")
    monkeypatch.setattr(settings, "pexels_api_key", "")

    res = await hotels.buscar_hoteles("Zagreb", "2026-09-10", "2026-09-14")

    assert res["precision"] == "real"
    assert [h["nombre"] for h in res["hoteles"]] == ["Art Hotel Like"]


# ── Detalle on-demand ─────────────────────────────────────────────────────

async def test_detalle_hotel_agrega_link(monkeypatch):
    async def fake_detalle(**kwargs):
        return {
            "nombre": "Hotel X", "descripcion": "desc",
            "fotos_urls": ["http://img1", "http://img2"],
            "habitaciones": [{"nombre": "Doble", "precio_total": 250}],
        }
    monkeypatch.setattr(hotels, "obtener_detalle_nl", fake_detalle)
    monkeypatch.setattr(settings, "travelpayouts_hotel_link", "")
    res = await hotels.detalle_hotel("123", "2026-10-10", "2026-10-14", 2, "Madrid")
    assert res["precision"] == "real"
    assert res["fotos_urls"] == ["http://img1", "http://img2"]
    assert res["habitaciones"][0]["link_reserva"].startswith("https://www.booking.com")


async def test_detalle_hotel_fallback(monkeypatch):
    async def fake_none(**kwargs):
        return None
    monkeypatch.setattr(hotels, "obtener_detalle_nl", fake_none)
    res = await hotels.detalle_hotel("123", "2026-10-10", "2026-10-14", 2, "Madrid")
    assert res["habitaciones"] == []
    assert "aviso" in res
