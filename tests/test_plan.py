# tests/test_plan.py
# Tests del orquestador de planes: modo flexible con mínimo de llamadas
# a la API de vuelos (búsqueda por mes + confirmación exacta) y medio de
# transporte elegido por el usuario (avión/bus/tren) con degradación a avión.

import pytest

import services.plan as plan


@pytest.fixture
def sin_clima_ni_actividades(monkeypatch):
    """Evita llamadas de red de clima/actividades dentro de generar_plan."""
    import services.weather as weather
    import services.activities as activities

    async def nada(*args, **kwargs):
        return None

    monkeypatch.setattr(weather, "obtener_clima", nada)
    monkeypatch.setattr(activities, "obtener_actividades", nada)


async def test_resolver_ciudad_destino_mapeo_local(monkeypatch):
    llamadas = []

    async def fake_aeropuerto(texto):
        llamadas.append(texto)
        return []

    monkeypatch.setattr(plan, "buscar_aeropuerto", fake_aeropuerto)
    assert await plan._resolver_ciudad_destino("MAD") == "Madrid"
    assert llamadas == []  # los IATA conocidos no llaman a la API


async def test_resolver_ciudad_destino_via_autocomplete(monkeypatch):
    async def fake_aeropuerto(texto):
        return [{"nombre": "Zagreb", "pais": "Croacia", "pais_codigo": "HR", "codigo": "ZAG"}]

    monkeypatch.setattr(plan, "buscar_aeropuerto", fake_aeropuerto)
    # ZAG no está en IATA_A_CIUDAD: sin esto, a Hotels.nl le llegaba el código
    # crudo y devolvía hoteles de Ámsterdam
    assert await plan._resolver_ciudad_destino("ZAG") == "Zagreb"


async def test_resolver_ciudad_destino_sin_resultados(monkeypatch):
    async def fake_aeropuerto(texto):
        return []

    monkeypatch.setattr(plan, "buscar_aeropuerto", fake_aeropuerto)
    assert await plan._resolver_ciudad_destino("xxx") == "XXX"


async def test_vuelos_flexibles_maximo_dos_llamadas(monkeypatch):
    llamadas = []

    async def fake_buscar(origen, destino, fs, fr, pax):
        llamadas.append((fs, fr))
        if len(fs) == 7:  # búsqueda por mes (YYYY-MM)
            return {"vuelos": [
                {"salida": "2026-10-18T10:00:00", "precio_total": 100, "precio_por_persona": 100},
                {"salida": "2026-10-05T10:00:00", "precio_total": 140, "precio_por_persona": 140},
            ], "precision": "exacta", "aviso": None}
        return {"vuelos": [
            {"salida": fs, "precio_total": 95, "precio_por_persona": 95},
        ], "precision": "exacta", "aviso": None}

    monkeypatch.setattr(plan, "buscar_vuelos", fake_buscar)

    res, fs, fr = await plan._vuelos_flexibles("BOG", "MAD", "2026-10-01", "2026-10-08", 1, 7)

    # Una búsqueda por mes + una exacta para la mejor ventana, nada más
    assert len(llamadas) == 2
    assert llamadas[0] == ("2026-10", "2026-10")
    # La ventana elegida arranca el día del vuelo más barato del mes
    assert fs == "2026-10-18"
    assert fr == "2026-10-25"
    assert "Modo flexible" in res["aviso"]
    assert res["vuelos"][0]["precio_total"] == 95


async def test_vuelos_flexibles_sin_vuelos_en_el_mes(monkeypatch):
    llamadas = []

    async def fake_buscar(origen, destino, fs, fr, pax):
        llamadas.append((fs, fr))
        if len(fs) == 7:
            return {"vuelos": [], "precision": "estimada", "aviso": None}
        return {"vuelos": [{"salida": fs, "precio_total": 200}], "precision": "estimada", "aviso": None}

    monkeypatch.setattr(plan, "buscar_vuelos", fake_buscar)

    res, fs, fr = await plan._vuelos_flexibles("BOG", "MAD", "2026-10-01", "2026-10-08", 1, 7)

    # Cae a la búsqueda con las fechas originales
    assert len(llamadas) == 2
    assert (fs, fr) == ("2026-10-01", "2026-10-08")
    assert res["vuelos"]


async def test_generar_plan_en_bus(monkeypatch, sin_clima_ni_actividades):
    async def fake_transporte(medio, origen, destino, fs, fr, pasajeros=1):
        return {"aviso": None, "precision": "estimada", "opciones": [
            {"medio": medio, "aerolinea": "", "salida": fs,
             "precio_por_persona": 60.0, "precio_total": 60.0},
        ]}

    async def fake_vuelos(*args, **kwargs):
        raise AssertionError("con medio_transporte=bus no debe buscar vuelos")

    monkeypatch.setattr(plan, "buscar_transporte", fake_transporte)
    monkeypatch.setattr(plan, "buscar_vuelos", fake_vuelos)

    res = await plan.generar_plan(
        "MAD", "BCN", "2026-08-10", "2026-08-17", presupuesto=800,
        incluir_hotel=False, medio_transporte="bus",
    )

    assert res["medio_transporte"] == "bus"
    assert res["plan_optimo"]["vuelo"]["medio"] == "bus"
    # El concepto de aeropuerto alternativo no aplica al transporte terrestre
    assert res["aeropuertos_alternativos"] == []


async def test_generar_plan_bus_no_viable_degrada_a_avion(monkeypatch, sin_clima_ni_actividades):
    llamadas_vuelo = []

    async def fake_vuelos(origen, destino, fs, fr, pax):
        llamadas_vuelo.append(destino)
        return {"vuelos": [
            {"aerolinea": "AV", "salida": fs, "precio_por_persona": 500.0, "precio_total": 500.0},
        ], "precision": "exacta", "aviso": None}

    monkeypatch.setattr(plan, "buscar_vuelos", fake_vuelos)

    # BOG→MAD ~8000 km: imposible en bus → el plan cae a avión con aviso
    res = await plan.generar_plan(
        "BOG", "MAD", "2026-08-10", "2026-08-17", presupuesto=900,
        incluir_hotel=False, medio_transporte="bus",
    )

    assert res["medio_transporte"] == "avion"
    assert "no es viable" in res["aviso"]
    assert "MAD" in llamadas_vuelo  # buscó vuelos como alternativa


def test_presupuesto_minimo_bus_menor_que_avion_en_ruta_corta():
    avion = plan.calcular_presupuesto_minimo("MAD", "BCN", noches=7, pasajeros=1, incluir_hotel=False)
    bus = plan.calcular_presupuesto_minimo(
        "MAD", "BCN", noches=7, pasajeros=1, incluir_hotel=False, medio_transporte="bus",
    )
    assert bus["presupuesto_minimo_sugerido"] < avion["presupuesto_minimo_sugerido"]


def test_presupuesto_minimo_bus_no_viable_usa_precio_de_avion():
    avion = plan.calcular_presupuesto_minimo("BOG", "MAD", noches=7, pasajeros=1, incluir_hotel=False)
    bus = plan.calcular_presupuesto_minimo(
        "BOG", "MAD", noches=7, pasajeros=1, incluir_hotel=False, medio_transporte="bus",
    )
    # Coherente con la degradación del plan: ruta no viable → mínimo de avión
    assert bus["presupuesto_minimo_sugerido"] == avion["presupuesto_minimo_sugerido"]
