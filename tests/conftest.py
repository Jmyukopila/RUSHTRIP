# tests/conftest.py
# Configuración común de tests: aísla las DBs SQLite a un dir temporal por test
# y expone utilidades para mockear respuestas HTTP sin tocar la red.

import sys
from pathlib import Path

import pytest

# Asegura que la raíz del repo esté en sys.path para importar core/, services/, main
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def temp_dbs(tmp_path, monkeypatch):
    """Redirige el cache persistente y el rate limiter a SQLite temporales por test."""
    import core.database_cache as dc
    import core.rate_limiter as rl

    monkeypatch.setattr(dc, "_DB_DIR", tmp_path)
    monkeypatch.setattr(dc, "_DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(rl, "_DB_DIR", tmp_path)
    monkeypatch.setattr(rl, "_DB_PATH", tmp_path / "rate.db")
    dc.init_db()
    rl.init_db()
    yield


class FakeResponse:
    """Respuesta HTTP falsa para mockear request_with_retry / http_client."""

    def __init__(self, status_code: int = 200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def fake_response():
    """Devuelve la clase FakeResponse para construir respuestas en los tests."""
    return FakeResponse
