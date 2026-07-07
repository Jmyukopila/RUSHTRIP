# tests/conftest.py
# Configuración común de tests: aísla las DBs SQLite a un dir temporal por test
# y expone utilidades para mockear respuestas HTTP sin tocar la red.

import os
import sys
from pathlib import Path

import pytest

# Aísla los tests de variables de entorno del desarrollador/producción.
# Los tests deben correr 100% offline y con SQLite local.
os.environ["SUPABASE_DB_URL"] = ""
os.environ["SUPABASE_URL"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["DEBUG"] = "true"
os.environ["OPENTRIPMAP_API_KEY"] = ""
os.environ["DEEPL_API_KEY"] = ""
os.environ["PEXELS_API_KEY"] = ""

# Asegura que la raíz del repo esté en sys.path para importar core/, services/, main
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def temp_dbs(tmp_path, monkeypatch):
    """Redirige el cache persistente y el rate limiter a SQLite temporales por test."""
    import core.database_cache as dc
    import core.rate_limiter as rl
    import core.auth_db as ad

    monkeypatch.setattr(dc, "_DB_DIR", tmp_path)
    monkeypatch.setattr(dc, "_DB_PATH", tmp_path / "cache.db")
    monkeypatch.setattr(rl, "_DB_DIR", tmp_path)
    monkeypatch.setattr(rl, "_DB_PATH", tmp_path / "rate.db")
    monkeypatch.setattr(ad, "_DB_DIR", tmp_path)
    monkeypatch.setattr(ad, "_DB_PATH", tmp_path / "auth.db")
    dc.init_db()
    rl.init_db()
    ad.init_db()

    # Los contadores anti fuerza bruta viven en memoria de modulo: limpiarlos
    # para que los fallos de login de un test no bloqueen al siguiente.
    import services.auth as auth_service
    auth_service._INTENTOS.clear()

    yield


@pytest.fixture(autouse=True)
def osm_offline(monkeypatch):
    """
    Evita que la verificación de rutas (OSRM/Overpass) toque la red en tests:
    por defecto las llamadas fallan y el servicio cae al heurístico por
    distancia. Los tests que necesiten respuestas OSM concretas re-parchean
    services.transport.request_with_retry localmente.
    """
    import services.transport as transport
    from core.errors import ExternalAPIError

    async def _sin_red(*args, **kwargs):
        raise ExternalAPIError("OSM deshabilitado en tests")

    monkeypatch.setattr(transport, "request_with_retry", _sin_red, raising=False)


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
