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
