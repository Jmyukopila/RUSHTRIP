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
