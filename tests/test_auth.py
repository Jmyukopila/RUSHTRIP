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
               nombre="Vero Vega", telefono="+57 300 123 4567", pais="Colombia",
               acepta_terminos=True):
    return client.post("/auth/register", json={
        "email": email, "password": password, "nombre": nombre,
        "telefono": telefono, "pais": pais, "acepta_terminos": acepta_terminos,
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
        "nombre": "Zoe Diaz", "pais": "México", "acepta_terminos": True,
    })
    assert r.status_code == 200
    assert r.json()["usuario"]["telefono"] == ""


def test_registro_sin_aceptar_terminos_falla(client):
    # El consentimiento se valida en el servidor, no solo en el checkbox del cliente.
    r = _registrar(client, acepta_terminos=False)
    assert r.status_code == 422
    assert "terminos" in r.json()["detail"].lower()


def test_registro_terminos_ausente_falla(client):
    # Falta el campo por completo: Pydantic lo rechaza (campo obligatorio).
    r = client.post("/auth/register", json={
        "email": "sinterminos@ejemplo.com", "password": "secreta123",
        "nombre": "Sin Terminos", "pais": "Colombia",
    })
    assert r.status_code == 422


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


def test_login_bloquea_tras_intentos_fallidos(client):
    # Tras 5 fallos consecutivos la cuenta queda bloqueada temporalmente,
    # incluso si el sexto intento trae la contrasena correcta.
    _registrar(client)
    for _ in range(5):
        r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "mala12345"})
        assert r.status_code in (422, 429)
    r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "secreta123"})
    assert r.status_code == 429
    assert "intentos" in r.json()["detail"].lower()


def test_login_bloqueo_cuenta_email_inexistente(client):
    # Los fallos tambien cuentan para emails no registrados: el bloqueo no
    # debe delatar que cuentas existen.
    for _ in range(5):
        client.post("/auth/login", json={"email": "nadie@ejemplo.com", "password": "mala12345"})
    r = client.post("/auth/login", json={"email": "nadie@ejemplo.com", "password": "mala12345"})
    assert r.status_code == 429


def test_login_exitoso_resetea_contador(client):
    # Un login correcto antes del bloqueo limpia el contador de fallos.
    _registrar(client)
    for _ in range(4):
        client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "mala12345"})
    r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "secreta123"})
    assert r.status_code == 200
    # El siguiente fallo vuelve a contar desde cero: 422, no 429.
    r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "mala12345"})
    assert r.status_code == 422


def test_login_bloqueo_expira(client):
    # Vencido el bloqueo, la cuenta vuelve a aceptar credenciales correctas.
    import services.auth as auth_service

    _registrar(client)
    for _ in range(5):
        client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "mala12345"})
    auth_service._INTENTOS["viajero@ejemplo.com"]["bloqueado_hasta"] = 0.0
    r = client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "secreta123"})
    assert r.status_code == 200


def test_logout_invalida_token(client):
    token = _registrar(client).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


# ─── Recuperacion de contrasena y verificacion de email ─────────────────────

def _token_de(tipo, usuario_id=None):
    """Lee el ultimo token de un tipo desde la DB SQLite temporal del test."""
    import core.auth_db as ad
    with ad._get_db() as conn:
        q = "SELECT token FROM tokens_auth WHERE tipo = ?"
        params = [tipo]
        if usuario_id is not None:
            q += " AND usuario_id = ?"
            params.append(usuario_id)
        row = conn.execute(q + " ORDER BY created_at DESC LIMIT 1", params).fetchone()
        return row["token"] if row else None


def test_registro_crea_usuario_no_verificado(client):
    data = _registrar(client).json()
    assert data["usuario"]["email_verificado"] is False


def test_forgot_password_respuesta_generica(client):
    _registrar(client)
    # Correo existente y correo inexistente devuelven la MISMA respuesta 200.
    r1 = client.post("/auth/forgot-password", json={"email": "viajero@ejemplo.com"})
    r2 = client.post("/auth/forgot-password", json={"email": "nadie@ejemplo.com"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()
    # Solo el correo real genera un token de reset.
    assert _token_de("reset") is not None


def test_reset_password_cambia_y_cierra_sesion(client):
    token_sesion = _registrar(client).json()["token"]
    headers = {"Authorization": f"Bearer {token_sesion}"}
    assert client.get("/auth/me", headers=headers).status_code == 200

    client.post("/auth/forgot-password", json={"email": "viajero@ejemplo.com"})
    reset_token = _token_de("reset")
    r = client.post("/auth/reset-password", json={"token": reset_token, "password": "nuevaClave99"})
    assert r.status_code == 200

    # La sesion previa quedo invalidada por el reset.
    assert client.get("/auth/me", headers=headers).status_code == 401
    # La password vieja ya no sirve; la nueva si.
    assert client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "secreta123"}).status_code == 422
    assert client.post("/auth/login", json={"email": "viajero@ejemplo.com", "password": "nuevaClave99"}).status_code == 200


def test_reset_password_token_invalido_falla(client):
    r = client.post("/auth/reset-password", json={"token": "token-inexistente-largo", "password": "otraClave123"})
    assert r.status_code == 422


def test_reset_password_corta_falla(client):
    _registrar(client)
    client.post("/auth/forgot-password", json={"email": "viajero@ejemplo.com"})
    reset_token = _token_de("reset")
    r = client.post("/auth/reset-password", json={"token": reset_token, "password": "corta"})
    assert r.status_code == 422


def test_verify_email_flow(client):
    usuario_id = _registrar(client).json()["usuario"]["id"]
    verif_token = _token_de("verificacion", usuario_id)
    assert verif_token is not None

    r = client.post("/auth/verify-email", json={"token": verif_token})
    assert r.status_code == 200
    assert r.json()["usuario"]["email_verificado"] is True

    # El token es de un solo uso: reutilizarlo falla.
    r2 = client.post("/auth/verify-email", json={"token": verif_token})
    assert r2.status_code == 422


def test_resend_verification_requiere_sesion(client):
    assert client.post("/auth/resend-verification").status_code == 401
