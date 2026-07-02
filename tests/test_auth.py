# tests/test_auth.py
# Tests de registro, login y proteccion del endpoint de plan.
# No tocan la red: usan las DBs SQLite temporales del conftest.

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import main
    with TestClient(main.app) as c:
        yield c


def _registrar(client, email="viajero@ejemplo.com", password="secreta123",
               nombre="Vero Vega", telefono="+57 300 123 4567", pais="Colombia"):
    return client.post("/auth/register", json={
        "email": email, "password": password, "nombre": nombre,
        "telefono": telefono, "pais": pais,
    })


def test_registro_devuelve_usuario_y_token(client):
    r = _registrar(client)
    assert r.status_code == 200
    data = r.json()
    assert data["usuario"]["email"] == "viajero@ejemplo.com"
    assert data["usuario"]["nombre"] == "Vero Vega"
    assert data["usuario"]["telefono"] == "+57 300 123 4567"
    assert data["usuario"]["pais"] == "Colombia"
    assert "password" not in data["usuario"]
    assert len(data["token"]) > 20


def test_registro_sin_nombre_falla(client):
    r = client.post("/auth/register", json={
        "email": "x@ejemplo.com", "password": "secreta123",
        "telefono": "+57 300 123 4567", "pais": "Colombia",
    })
    assert r.status_code == 422


def test_registro_telefono_invalido_falla(client):
    # 8 caracteres pero no son digitos: si se envia telefono, debe ser valido.
    r = _registrar(client, telefono="abcdefgh")
    assert r.status_code == 422


def test_registro_sin_telefono_ok(client):
    # El telefono es opcional: registrarse sin el debe funcionar.
    r = client.post("/auth/register", json={
        "email": "z@ejemplo.com", "password": "secreta123",
        "nombre": "Zoe Diaz", "pais": "México",
    })
    assert r.status_code == 200
    assert r.json()["usuario"]["telefono"] == ""


def test_registro_sin_pais_falla(client):
    r = client.post("/auth/register", json={
        "email": "y@ejemplo.com", "password": "secreta123",
        "nombre": "Ana Ruiz", "telefono": "+57 300 123 4567",
    })
    assert r.status_code == 422


def test_registro_email_duplicado_falla(client):
    _registrar(client)
    r = _registrar(client)
    assert r.status_code == 422
    assert "correo" in r.json()["detail"].lower()


def test_registro_password_corta_falla(client):
    r = _registrar(client, password="corta")
    assert r.status_code == 422


def test_registro_email_invalido_falla(client):
    r = client.post("/auth/register", json={"email": "no-es-email", "password": "secreta123"})
    assert r.status_code == 422


def test_login_correcto(client):
    _registrar(client)
    r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "secreta123"})
    assert r.status_code == 200
    assert r.json()["token"]


def test_login_password_incorrecta(client):
    _registrar(client)
    r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "otra12345"})
    assert r.status_code == 422


def test_login_usuario_inexistente(client):
    r = client.post("/auth/login", json={"email": "nadie@ejemplo.com", "password": "secreta123"})
    assert r.status_code == 422


def test_me_requiere_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_con_token_valido(client):
    token = _registrar(client).json()["token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == "viajero@ejemplo.com"


def test_plan_sin_sesion_devuelve_401(client):
    r = client.post("/plan/", json={
        "origen": "BOG", "destino": "MAD",
        "fecha_salida": "2026-12-15", "fecha_regreso": "2026-12-22",
        "presupuesto": 800,
    })
    assert r.status_code == 401


def test_logout_invalida_token(client):
    token = _registrar(client).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401
