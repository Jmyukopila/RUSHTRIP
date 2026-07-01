# tests/test_flights.py
# Tests de los links de compra de vuelos (afiliación Aviasales vía marker).

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
