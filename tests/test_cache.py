# tests/test_cache.py
# Tests del cache en memoria (TTLCache) y del cache persistente SQLite.

import time

from core.cache import TTLCache
from core import database_cache as dc


# ── TTLCache en memoria ───────────────────────────────────────────────────

def test_ttlcache_set_get():
    c = TTLCache(ttl_seconds=100)
    c.set("k", {"a": 1})
    assert c.get("k") == {"a": 1}
    assert "k" in c
    assert c.get("missing") is None


def test_ttlcache_get_expired():
    c = TTLCache(ttl_seconds=0)  # expira de inmediato
    c.set("k", "v")
    time.sleep(0.01)
    assert c.get_expired("k") == "v"  # stale: devuelve aunque expiró, sin borrar
    assert c.get("k") is None         # get respeta la expiración (y borra)


def test_ttlcache_clear():
    c = TTLCache(ttl_seconds=100)
    c.set("k", "v")
    c.clear()
    assert c.get("k") is None


# ── Cache persistente SQLite (usa el temp_dbs autouse de conftest) ────────

def test_database_cache_roundtrip():
    dc.cache_set("key1", {"x": 1}, provider="test", ttl_seconds=100)
    assert dc.cache_get("key1") == {"x": 1}


def test_database_cache_expira():
    dc.cache_set("key2", {"y": 2}, provider="test", ttl_seconds=0)
    time.sleep(0.01)
    assert dc.cache_get("key2") is None  # expirado


def test_database_cache_stale():
    dc.cache_set("key3", {"z": 3}, provider="test", ttl_seconds=0)
    time.sleep(0.01)
    # stale devuelve el valor aunque haya expirado (fallback cuando la API falla)
    assert dc.cache_get_stale("key3") == {"z": 3}


def test_database_cache_miss():
    assert dc.cache_get("no-existe") is None
    assert dc.cache_get_stale("no-existe") is None
