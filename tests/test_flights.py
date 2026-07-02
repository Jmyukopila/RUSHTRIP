# tests/test_flights.py
# Tests de los links de compra de vuelos (afiliación Aviasales vía marker)
# y de la rotación de tokens de Travelpayouts.

from core.config import settings
import services.flights as flights


def test_link_compra_sin_query():
    out = flights.link_compra("/search/BOG1012MAD1412", "723238")
    assert out == "https://www.aviasales.com/search/BOG1012MAD1412?marker=723238"


def test_link_compra_con_query_existente():
    out = flights.link_compra("/search/x?a=1", "723238")
    assert out.startswith("https://www.aviasales.com")
    assert "&marker=723238" in out  # usa & porque el link ya tiene query


def test_link_compra_fallback():
    out = flights.link_compra_fallback("bog", "mad", "2026-10-10", "723238")
    assert out.startswith("https://www.aviasales.com/search/BOGMAD")
    assert out.endswith("?marker=723238")
    assert "20261010" in out  # fecha sin guiones


async def test_buscar_rota_tokens_en_403(monkeypatch, fake_response):
    tokens_usados = []

    async def fake_req(method, url, **kwargs):
        token = kwargs["params"]["token"]
        tokens_usados.append(token)
        if token == "t1":
            return fake_response(403, {})
        return fake_response(200, {"success": True, "data": [
            {"airline": "AV", "price": 100, "transfers": 0,
             "departure_at": "2026-10-10T08:00:00", "link": "/search/x"},
        ]})

    monkeypatch.setattr(flights, "request_with_retry", fake_req)
    monkeypatch.setattr(settings, "travelpayouts_token", "t1")
    monkeypatch.setattr(settings, "travelpayouts_token_2", "t2")
    monkeypatch.setattr(settings, "travelpayouts_token_3", "")

    res = await flights._buscar("BOG", "MAD", "2026-10-10", "2026-10-14", 1)

    assert tokens_usados == ["t1", "t2"]  # rotó al segundo token tras el 403
    assert len(res["vuelos"]) == 1
    assert res["vuelos"][0]["precio_por_persona"] == 100.0
