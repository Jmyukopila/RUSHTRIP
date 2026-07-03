# tests/test_activities_boost.py
# Tests de la personalización de actividades según contexto del plan.
# No tocan la red: usan el dataset curado local y funciones puras.

import pytest

from services.activities import (
    _boost_por_contexto,
    _bucket_lluvia,
    _bucket_pasajeros,
    _calcular_noches,
    _score_actividad,
)


def _act(nombre: str, categoria: str, precio: float) -> dict:
    """Factory mínima para actividades de prueba."""
    return {
        "nombre": nombre,
        "categoria": categoria,
        "precio_estimado": precio,
        "gratis": precio == 0,
    }


def test_calcular_noches():
    assert _calcular_noches("2026-08-10", "2026-08-15") == 5
    assert _calcular_noches("2026-08-10", "2026-08-11") == 1
    assert _calcular_noches("2026-08-15", "2026-08-10") == 0
    assert _calcular_noches("", "2026-08-15") == 0


def test_bucket_lluvia():
    assert _bucket_lluvia(None) == "sin"
    assert _bucket_lluvia({}) == "sin"
    assert _bucket_lluvia({"dias": []}) == "sin"
    assert _bucket_lluvia({"dias": [{"prob_lluvia": 80}]}) == "alta"
    assert _bucket_lluvia({"dias": [{"prob_lluvia": 30}]}) == "media"
    assert _bucket_lluvia({"dias": [{"prob_lluvia": 10}]}) == "baja"


def test_bucket_pasajeros():
    assert _bucket_pasajeros(1) == "solo"
    assert _bucket_pasajeros(2) == "pareja"
    assert _bucket_pasajeros(3) == "pareja"
    assert _bucket_pasajeros(4) == "grupo"
    assert _bucket_pasajeros(6) == "grupo"


def test_tier_economico_prefiere_gratis():
    actividades = [
        _act("Tour privado", "Tour gastronómico", 80),
        _act("Museo", "Museo", 10),
        _act("Mirador", "Mirador", 0),
        _act("Parque de atracciones", "Parque de atracciones", 110),
    ]
    resultado = _boost_por_contexto(
        actividades, tier="economico", clima=None, pasajeros=2,
        fecha_salida="2026-08-10", fecha_regreso="2026-08-15",
    )
    assert resultado[0]["nombre"] == "Mirador"
    assert resultado[1]["nombre"] == "Museo"


def test_tier_premium_prefiere_experiencias_premium():
    actividades = [
        _act("Mirador", "Mirador", 0),
        _act("Tour gastronómico", "Tour gastronómico", 60),
        _act("Museo", "Museo", 10),
        _act("Espectáculo", "Espectáculo", 50),
    ]
    resultado = _boost_por_contexto(
        actividades, tier="premium", clima=None, pasajeros=2,
        fecha_salida="2026-08-10", fecha_regreso="2026-08-15",
    )
    # premium valora más tour gastronómico y espectáculo
    assert resultado[0]["nombre"] == "Tour gastronómico"
    assert resultado[1]["nombre"] == "Espectáculo"


def test_clima_lluvioso_sube_indoor():
    actividades = [
        _act("Playa", "Playa", 0),
        _act("Museo", "Museo", 15),
        _act("Mirador", "Mirador", 0),
        _act("Espectáculo", "Espectáculo", 40),
    ]
    clima = {"dias": [{"prob_lluvia": 85}, {"prob_lluvia": 90}]}
    resultado = _boost_por_contexto(
        actividades, tier="premium", clima=clima, pasajeros=2,
        fecha_salida="2026-08-10", fecha_regreso="2026-08-12",
    )
    # Con lluvia y tier premium, los indoor premium (Espectáculo) ganan.
    indoor = {"Museo", "Espectáculo"}
    outdoor = {"Playa", "Mirador"}
    assert resultado[0]["nombre"] == "Espectáculo"
    assert resultado[1]["nombre"] == "Museo"
    assert resultado[2]["nombre"] in outdoor
    assert resultado[3]["nombre"] in outdoor


def test_viaje_corto_penaliza_excursion_larga():
    actividades = [
        _act("Excursión día completo", "Excursión", 60),
        _act("Museo", "Museo", 10),
        _act("Tour guiado", "Tour guiado", 20),
    ]
    resultado = _boost_por_contexto(
        actividades, tier="estandar", clima=None, pasajeros=2,
        fecha_salida="2026-08-10", fecha_regreso="2026-08-11",  # 1 noche
    )
    assert resultado[-1]["nombre"] == "Excursión día completo"
    assert resultado[0]["nombre"] == "Museo"


def test_grupo_familiar_prefiere_familiar():
    actividades = [
        _act("Tour gastronómico", "Tour gastronómico", 60),
        _act("Parque de atracciones", "Parque de atracciones", 110),
        _act("Museo", "Museo", 10),
    ]
    resultado = _boost_por_contexto(
        actividades, tier="premium", clima=None, pasajeros=5,
        fecha_salida="2026-08-10", fecha_regreso="2026-08-15",
    )
    # Parque de atracciones es familiar y premium; con grupo y tier premium sube.
    assert resultado[0]["nombre"] == "Parque de atracciones"


def test_score_actividad_categoria_desconocida_no_rompe():
    act = _act("Algo raro", "Categoría inexistente", 25)
    score = _score_actividad(act, "estandar", "sin", "solo", 5)
    assert isinstance(score, float)


@pytest.mark.asyncio
async def test_obtener_actividades_usa_contexto_curado():
    """Sin OPENTRIPMAP_API_KEY, el curado se reordena según el contexto."""
    from services.activities import obtener_actividades

    resultado = await obtener_actividades(
        "Madrid", iata="MAD", limite=8,
        tier="economico", fecha_salida="2026-08-10", fecha_regreso="2026-08-15",
        clima=None, pasajeros=2,
    )
    assert resultado["precision"] == "estimada"
    assert len(resultado["actividades"]) > 0
    # En Madrid el primer elemento del curado es Museo del Prado (de pago);
    # con economico debería subir una actividad gratis si existe.
    nombres = [a["nombre"] for a in resultado["actividades"]]
    assert "Parque del Retiro" in nombres


@pytest.mark.asyncio
async def test_obtener_actividades_backward_compat():
    """Llamar sin kwargs de contexto sigue funcionando (defaults)."""
    from services.activities import obtener_actividades

    resultado = await obtener_actividades("Bogotá", iata="BOG", limite=5)
    assert resultado["precision"] == "estimada"
    assert len(resultado["actividades"]) == 5


# ─────────────────────────────────────────────────────────────────────────────
# Tests Fase 3 — dataset curado expandido y fusión curado + OpenTripMap
# ─────────────────────────────────────────────────────────────────────────────


def test_tiene_curado():
    from services.activities import _tiene_curado

    assert _tiene_curado("BOG", "Bogotá") is True
    assert _tiene_curado(None, "Tokio") is True
    assert _tiene_curado("XXX", "Ciudad Inexistente") is False


def test_fusionar_actividades_prioriza_curado_y_evita_duplicados():
    from services.activities import _fusionar_actividades

    curado = [
        {"nombre": "Museo del Prado", "categoria": "Museo"},
        {"nombre": "Parque del Retiro", "categoria": "Parque / Naturaleza"},
    ]
    reales = [
        {"nombre": "Museo del Prado", "categoria": "Museo"},
        {"nombre": "Real Madrid Tour", "categoria": "Atracción"},
    ]
    resultado = _fusionar_actividades(curado, reales, 3)
    assert len(resultado) == 3
    nombres = [a["nombre"] for a in resultado]
    assert nombres == ["Museo del Prado", "Parque del Retiro", "Real Madrid Tour"]


# ─────────────────────────────────────────────────────────────────────────────
# Tests Fase 2 — enriquecimiento OpenTripMap (/places/xid, fotos, traducción)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enriquecer_poi_opentripmap(monkeypatch):
    from services.activities import _enriquecer_poi_opentripmap

    class FakeResp:
        status_code = 200
        def json(self):
            return {
                "xid": "test-xid",
                "name": "Museo Test",
                "image": "https://example.com/museo.jpg",
                "wikipedia_extracts": {"text": "A great museum in the city."},
            }

    async def fake_request(*args, **kwargs):
        return FakeResp()

    monkeypatch.setattr("services.activities.request_with_retry", fake_request)

    detalle = await _enriquecer_poi_opentripmap("test-xid", "Madrid")
    assert detalle["descripcion"] == "A great museum in the city."
    assert "museo.jpg" in detalle["foto_url"]


@pytest.mark.asyncio
async def test_traducir_descripciones_sin_key_devuelve_original():
    from services.activities import _traducir_descripciones

    textos = ["A great museum.", "A nice park."]
    resultado = await _traducir_descripciones(textos)
    assert resultado == textos


@pytest.mark.asyncio
async def test_traducir_descripciones_con_deepl(monkeypatch):
    from services.activities import _traducir_descripciones
    from core.config import settings

    monkeypatch.setattr(settings, "deepl_api_key", "fake-deepl-key")

    class FakeResp:
        status_code = 200
        def json(self):
            return {
                "translations": [
                    {"text": "Un gran museo."},
                    {"text": "Un bonito parque."},
                ]
            }

    async def fake_request(*args, **kwargs):
        return FakeResp()

    monkeypatch.setattr("services.activities.request_with_retry", fake_request)

    textos = ["A great museum.", "A nice park."]
    resultado = await _traducir_descripciones(textos)
    assert resultado == ["Un gran museo.", "Un bonito parque."]


@pytest.mark.asyncio
async def test_consultar_opentripmap_enriquece_descripcion_y_foto(monkeypatch):
    from services.activities import _consultar_opentripmap

    class RadiusResp:
        status_code = 200
        def json(self):
            return [
                {
                    "xid": "xid-1",
                    "name": "Museo del Test",
                    "rate": 5,
                    "kinds": "museums,interesting_places",
                },
            ]

    class DetailResp:
        status_code = 200
        def json(self):
            return {
                "xid": "xid-1",
                "image": "https://example.com/test.jpg",
                "wikipedia_extracts": {"text": "Museum description in english."},
            }

    class PexelsResp:
        status_code = 200
        def json(self):
            return {
                "photos": [
                    {"src": {"medium": "https://pexels.com/fallback.jpg"}}
                ]
            }

    calls = []
    async def fake_request(method, url, **kwargs):
        calls.append((method, url))
        if "radius" in url:
            return RadiusResp()
        if "xid" in url:
            return DetailResp()
        if "pexels" in url:
            return PexelsResp()
        return RadiusResp()

    monkeypatch.setattr("services.activities.request_with_retry", fake_request)

    actividades = await _consultar_opentripmap(40.0, -3.0, "Madrid", 8)

    assert len(actividades) == 1
    act = actividades[0]
    assert act["nombre"] == "Museo del Test"
    assert "foto_url" in act
    assert act["foto_url"] == "https://example.com/test.jpg"
    # Descripción enriquecida (sin DeepL key queda en inglés)
    assert "english" in act["descripcion"].lower()


@pytest.mark.asyncio
async def test_obtener_actividades_con_opentripmap(monkeypatch):
    """Si hay OPENTRIPMAP_API_KEY y responde, devuelve precision 'real'."""
    from services.activities import obtener_actividades
    from core.config import settings

    monkeypatch.setattr(settings, "opentripmap_api_key", "fake-otm-key")
    monkeypatch.setattr(settings, "pexels_api_key", "")

    class RadiusResp:
        status_code = 200
        def json(self):
            return [
                {
                    "xid": "xid-1",
                    "name": "Parque Test",
                    "rate": 5,
                    "kinds": "gardens_and_parks,interesting_places",
                },
            ]

    class DetailResp:
        status_code = 200
        def json(self):
            return {
                "xid": "xid-1",
                "image": "",
                "wikipedia_extracts": {"text": "A nice park."},
            }

    async def fake_request(method, url, **kwargs):
        if "radius" in url:
            return RadiusResp()
        if "xid" in url:
            return DetailResp()
        return RadiusResp()

    monkeypatch.setattr("services.activities.request_with_retry", fake_request)

    resultado = await obtener_actividades("Madrid", iata="MAD", limite=8)
    assert resultado["precision"] == "real"
    # Madrid tiene 5 curadas + 1 real = 6 actividades (sin duplicados)
    assert len(resultado["actividades"]) == 6
    nombres = [a["nombre"] for a in resultado["actividades"]]
    assert "Parque Test" in nombres
    assert any(a["fuente"] == "curado" for a in resultado["actividades"])
    assert any(a["fuente"] == "opentripmap" for a in resultado["actividades"])
