# tests/test_transport.py
# Tests del servicio de transporte terrestre (bus/tren): viabilidad de rutas
# por distancia, precios estimados, CO2, links de compra y contrato de salida.

import pytest

import services.transport as transport


# ---------- viabilidad de rutas ----------

def test_ruta_viable_bus_corta():
    # MAD→BCN ~490 km: viable en bus
    viable, km = transport.ruta_viable("bus", "MAD", "BCN")
    assert viable is True
    assert 400 < km < 700


def test_ruta_no_viable_transoceanica():
    # BOG→MAD ~8000 km: hay coords pero excede el límite de cualquier medio
    viable, km = transport.ruta_viable("bus", "BOG", "MAD")
    assert viable is False
    assert km is not None and km > transport.LIMITE_KM["bus"]


def test_tren_alcanza_mas_lejos_que_bus():
    # MAD→VIE ~1800 km: fuera del límite de bus (1500) pero dentro del de tren (2500)
    viable_bus, _ = transport.ruta_viable("bus", "MAD", "VIE")
    viable_tren, _ = transport.ruta_viable("tren", "MAD", "VIE")
    assert viable_bus is False
    assert viable_tren is True


def test_ruta_sin_coords_no_verificable():
    # IATA desconocido: sin coords no se puede verificar → (False, None)
    assert transport.ruta_viable("bus", "XXX", "MAD") == (False, None)


# ---------- precios y CO2 ----------

def test_precio_minimo_proporcional_a_distancia():
    corto = transport.precio_transporte_minimo("bus", "MAD", "BCN")   # ~490 km
    largo = transport.precio_transporte_minimo("bus", "MAD", "FCO")   # ~1360 km
    assert largo > corto > 0


def test_precio_minimo_respeta_piso_por_trayecto():
    # JFK→LGA ~17 km: la tarifa por km queda debajo del piso → aplica el mínimo x2 (ida y vuelta)
    precio = transport.precio_transporte_minimo("bus", "JFK", "LGA")
    assert precio == transport.PRECIO_MINIMO_TRAYECTO["bus"] * 2


def test_co2_terrestre_menor_que_avion():
    from services.flights import estimar_co2
    _, km = transport.ruta_viable("tren", "MAD", "BCN")
    co2_tren = transport.estimar_co2_transporte("tren", km)
    co2_bus = transport.estimar_co2_transporte("bus", km)
    co2_avion = estimar_co2("MAD", "BCN")
    assert co2_tren < co2_bus < co2_avion


# ---------- link de compra ----------

def test_link_compra_usa_nombres_de_ciudad():
    link = transport.link_compra_transporte("bus", "MAD", "BCN")
    assert link.startswith("https://www.rome2rio.com/es/map/")
    assert "Madrid" in link and "Barcelona" in link


def test_link_compra_ciudades_con_espacios_van_escapadas():
    link = transport.link_compra_transporte("tren", "JFK", "MAD")
    assert "Nueva%20York" in link


# ---------- buscar_transporte ----------

async def test_buscar_transporte_contrato_de_salida():
    res = await transport.buscar_transporte("bus", "MAD", "BCN", "2026-08-10", "2026-08-17", 2)

    assert res["precision"] == "estimada"
    assert res["aviso"]
    opciones = res["opciones"]
    assert len(opciones) >= 3

    for o in opciones:
        assert o["medio"] == "bus"
        assert o["tipo"] == "estimado"
        assert o["aerolinea"] == ""            # no matchea el filtro premium de aerolíneas
        assert o["logo_url"] == ""
        assert o["origen"] == "MAD" and o["destino"] == "BCN"
        assert o["pasajeros"] == 2
        assert o["precio_total"] == pytest.approx(o["precio_por_persona"] * 2, abs=0.02)
        assert o["duracion_minutos"] > 0
        assert o["distancia_km"] > 0
        assert o["co2_kg"] > 0
        assert "rome2rio.com" in o["link_compra"]

    # Ordenadas por precio ascendente
    precios = [o["precio_por_persona"] for o in opciones]
    assert precios == sorted(precios)


async def test_buscar_transporte_cachea_resultado():
    args = ("tren", "MAD", "BCN", "2026-08-10", "2026-08-17", 1)
    primera = await transport.buscar_transporte(*args)
    segunda = await transport.buscar_transporte(*args)
    # El estimado tiene variación aleatoria: si la segunda llamada es idéntica,
    # vino del cache y no se re-estimó.
    assert primera["opciones"] == segunda["opciones"]


async def test_buscar_transporte_ruta_no_viable_devuelve_vacio_con_aviso():
    res = await transport.buscar_transporte("bus", "BOG", "MAD", "2026-08-10", "2026-08-17", 1)
    assert res["opciones"] == []
    assert "no es viable" in res["aviso"]


async def test_buscar_transporte_medio_invalido():
    with pytest.raises(ValueError):
        await transport.buscar_transporte("barco", "MAD", "BCN", "2026-08-10", "2026-08-17", 1)
