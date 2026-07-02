# tests/test_cars.py
# Tests del servicio de coches: cache persistente (la cuota de RapidAPI es
# mensual y escasa) y fallback estimado cacheado cuando la API falla.

from core.config import settings
from core.errors import ExternalAPIError
import services.cars as cars


async def test_buscar_coches_cachea_resultado_real(monkeypatch, fake_response):
    llamadas = []

    async def fake_req(method, url, **kwargs):
        llamadas.append(url)
        return fake_response(200, {"data": [
            {"name": "Econ", "price": "50", "transmission": "Manual", "seats": 4,
             "bags": 2, "currency": "USD", "provider": "X", "deep_link": "http://x",
             "image": ""},
        ]})

    monkeypatch.setattr(cars, "request_with_retry", fake_req)
    monkeypatch.setattr(settings, "rapidapi_key", "k1")
    monkeypatch.setattr(settings, "rapidapi_key_2", "")
    monkeypatch.setattr(settings, "rapidapi_key_3", "")

    r1 = await cars.buscar_coches("MAD", "2026-10-10", "2026-10-14")
    r2 = await cars.buscar_coches("MAD", "2026-10-10", "2026-10-14")

    assert len(llamadas) == 1  # la segunda búsqueda sale del cache
    assert r1["coches"][0]["precio_total"] == 50.0
    assert r2["coches"] == r1["coches"]


async def test_buscar_coches_fallback_cacheado(monkeypatch):
    llamadas = []

    async def fake_fail(method, url, **kwargs):
        llamadas.append(url)
        raise ExternalAPIError("Rate limit excedido en rapidapi", provider="rapidapi", status_code=429)

    monkeypatch.setattr(cars, "request_with_retry", fake_fail)
    monkeypatch.setattr(settings, "rapidapi_key", "k1")
    monkeypatch.setattr(settings, "rapidapi_key_2", "")
    monkeypatch.setattr(settings, "rapidapi_key_3", "")

    r1 = await cars.buscar_coches("BOG", "2026-10-10", "2026-10-14")
    r2 = await cars.buscar_coches("BOG", "2026-10-10", "2026-10-14")

    # El fallback estimado queda cacheado (TTL corto): no se golpea la API caída en cada plan
    assert len(llamadas) == 1
    assert len(r1["coches"]) == 4  # 4 categorías estimadas
    assert r1["aviso"]
    assert r2["coches"] == r1["coches"]


async def test_buscar_coches_rota_keys(monkeypatch, fake_response):
    keys_usadas = []

    async def fake_req(method, url, **kwargs):
        key = kwargs["headers"]["x-rapidapi-key"]
        keys_usadas.append(key)
        if key == "k1":
            return fake_response(403, {})
        return fake_response(200, {"data": [
            {"name": "Econ", "price": "40", "currency": "USD"},
        ]})

    monkeypatch.setattr(cars, "request_with_retry", fake_req)
    monkeypatch.setattr(settings, "rapidapi_key", "k1")
    monkeypatch.setattr(settings, "rapidapi_key_2", "k2")
    monkeypatch.setattr(settings, "rapidapi_key_3", "")

    res = await cars.buscar_coches("LIM", "2026-10-10", "2026-10-14")

    assert keys_usadas == ["k1", "k2"]  # rotó a la segunda key tras el 403
    assert res["coches"][0]["precio_total"] == 40.0
