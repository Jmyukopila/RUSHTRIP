# tests/test_routes.py
# Tests de los endpoints vía TestClient. Se centran en validación (no tocan red):
# las fechas inválidas devuelven 422 antes de llamar a ningún servicio externo.

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import main
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200


def test_hotels_formato_fecha_invalido(client):
    r = client.get("/hotels/", params={"ciudad": "Madrid", "checkin": "10-10-2026", "checkout": "2026-10-14"})
    assert r.status_code == 422


def test_hotels_checkout_antes_de_checkin(client):
    r = client.get("/hotels/", params={"ciudad": "Madrid", "checkin": "2026-10-14", "checkout": "2026-10-10"})
    assert r.status_code == 422


def test_hotels_detalle_fecha_invalida(client):
    r = client.get("/hotels/detalle", params={"id": "1", "checkin": "bad", "checkout": "2026-10-14"})
    assert r.status_code == 422


def test_transport_medio_invalido(client):
    r = client.get("/transport/", params={
        "medio": "barco", "origen": "MAD", "destino": "BCN",
        "fecha_salida": "2026-08-10", "fecha_regreso": "2026-08-17",
    })
    assert r.status_code == 422


def test_transport_fecha_invalida(client):
    r = client.get("/transport/", params={
        "medio": "bus", "origen": "MAD", "destino": "BCN",
        "fecha_salida": "10-08-2026", "fecha_regreso": "2026-08-17",
    })
    assert r.status_code == 422


def test_transport_busqueda_valida(client):
    r = client.get("/transport/", params={
        "medio": "bus", "origen": "MAD", "destino": "BCN",
        "fecha_salida": "2026-08-10", "fecha_regreso": "2026-08-17", "pasajeros": 2,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["precision"] == "estimada"
    assert body["opciones"]
    assert body["opciones"][0]["medio"] == "bus"


def test_plan_request_medio_transporte_invalido():
    from pydantic import ValidationError
    from backend.routes.plan import PlanRequest

    with pytest.raises(ValidationError):
        PlanRequest(
            origen="MAD", destino="BCN",
            fecha_salida="2026-08-10", fecha_regreso="2026-08-17",
            presupuesto=500, medio_transporte="barco",
        )


def test_min_budget_en_bus_es_menor(client):
    params = {
        "origen": "MAD", "destino": "BCN",
        "fecha_salida": "2026-08-10", "fecha_regreso": "2026-08-17",
        "incluir_hotel": False,
    }
    r_avion = client.get("/plan/min-budget/", params=params)
    r_bus = client.get("/plan/min-budget/", params={**params, "medio_transporte": "bus"})
    assert r_avion.status_code == 200 and r_bus.status_code == 200
    assert (
        r_bus.json()["presupuesto_minimo_sugerido"]
        < r_avion.json()["presupuesto_minimo_sugerido"]
    )
