# tests/test_hotels_nl.py
# Tests de la integración Hotels.nl: helpers de mapeo y normalización de
# search.php / hotel.php con request_with_retry mockeado (sin red).

from core.config import settings
import services.hotels_nl as nl


def test_to_float():
    assert nl._to_float("12.5") == 12.5
    assert nl._to_float(None) == 0.0
    assert nl._to_float("abc") == 0.0


def test_stars_mappings():
    assert nl._stars_to_rating(5) == 9.0
    assert nl._rating_word(4) == "Muy bien"
    assert nl._stars_to_reviews(3) == 150


async def test_obtener_detalle_normaliza(monkeypatch, fake_response):
    payload = {
        "name": "Test Hotel",
        "descriptions": [{"title": "t", "text": "Una descripción larga"}],
        "images": [{"url": "http://img1", "category": "room"}, {"url": "http://img2"}],
        "rooms": [
            {"room_name": "Doble", "capacity": 2, "bedding": "1 king", "rates": [
                {"hotelsnl_hash": "h1", "meal": "Desayuno", "refundable": True,
                 "pricing": {"total_price": "300", "currency": "USD", "price_per_night": "75"}},
                {"hotelsnl_hash": "h2", "meal": "", "refundable": False,
                 "pricing": {"total_price": "250", "currency": "USD", "price_per_night": "62.5"}},
            ]},
            {"room_name": "Suite", "capacity": 3, "rates": [
                {"hotelsnl_hash": "h3", "pricing": {"total_price": "500", "currency": "USD"}},
            ]},
        ],
    }

    async def fake_req(method, url, **kwargs):
        return fake_response(200, payload)

    monkeypatch.setattr(settings, "hotelsnl_api_key", "x")
    monkeypatch.setattr(nl, "request_with_retry", fake_req)

    res = await nl.obtener_detalle(123, "2026-10-10", "2026-10-14", 2)
    assert res["nombre"] == "Test Hotel"
    assert res["fotos_urls"] == ["http://img1", "http://img2"]
    # Habitaciones ordenadas por precio ascendente
    assert [h["nombre"] for h in res["habitaciones"]] == ["Doble", "Suite"]
    # Se elige la tarifa más barata de cada habitación (250 = h2, no 300 = h1)
    assert res["habitaciones"][0]["precio_total"] == 250.0
    assert res["habitaciones"][0]["hotelsnl_hash"] == "h2"


async def test_obtener_detalle_sin_key(monkeypatch):
    monkeypatch.setattr(settings, "hotelsnl_api_key", "")
    assert await nl.obtener_detalle(123, "2026-10-10", "2026-10-14") is None


async def test_buscar_hoteles_nl_normaliza(monkeypatch, fake_response):
    payload = {
        "search": {"nights": 4},
        "hotels": [
            {"id": 99, "name": "Hotel Uno", "star_rating": 4, "address": "Calle 1",
             "city": "Madrid", "country_code": "ES", "image": "http://h1.jpg",
             "amenities": "WiFi, Piscina", "short_description": "desc",
             "rate": {"hotelsnl_hash": "hh", "pricing": {"total_price": "400", "currency": "USD"}, "room": {}}},
        ],
    }

    async def fake_req(method, url, **kwargs):
        return fake_response(200, payload)

    monkeypatch.setattr(settings, "hotelsnl_api_key", "x")
    monkeypatch.setattr(nl, "request_with_retry", fake_req)

    res = await nl.buscar_hoteles("Madrid", "2026-10-10", "2026-10-14")
    assert len(res) == 1
    h = res[0]
    assert h["nombre"] == "Hotel Uno"
    assert h["id_hotelsnl"] == 99
    assert h["precio_total"] == 400.0
    assert h["precio_noche"] == 100.0  # 400 / 4 noches
    assert h["tipo"] == "real"
    assert h["amenities"] == ["WiFi", "Piscina"]


async def test_buscar_hoteles_nl_403(monkeypatch, fake_response):
    async def fake_req(method, url, **kwargs):
        return fake_response(403, {})
    monkeypatch.setattr(settings, "hotelsnl_api_key", "x")
    monkeypatch.setattr(nl, "request_with_retry", fake_req)
    # 403 (key inválida) => None para que el servicio caiga al fallback
    assert await nl.buscar_hoteles("Madrid", "2026-10-10", "2026-10-14") is None
