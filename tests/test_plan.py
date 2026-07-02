# tests/test_plan.py
# Tests del orquestador de planes: modo flexible con mínimo de llamadas
# a la API de vuelos (búsqueda por mes + confirmación exacta).

import services.plan as plan


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
