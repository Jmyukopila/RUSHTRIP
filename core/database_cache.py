# core/database_cache.py
# Cache persistente SQLite con TTL, compartido entre workers
# WAL mode para máxima concurrencia de lecturas

import json
import logging
import random
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Ruta fija del archivo de cache (persistente entre reinicios)
_DB_DIR = Path(__file__).resolve().parent.parent / "cache"
_DB_PATH = _DB_DIR / "rushtrip_cache.db"

# Lock de escritura para evitar race conditions entre workers
_write_lock = threading.Lock()

# Las entradas vencidas se retienen este tiempo extra antes de borrarse:
# son el fallback de cache_get_stale cuando la API del proveedor falla
_STALE_RETENTION = 7 * 24 * 3600


def _get_db() -> sqlite3.Connection:
    """Abre conexion SQLite en WAL mode para lectura/escritura."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """Inicializa la base de datos de cache. Llama al startup."""
    _init_db()


def _init_db():
    """Crea la tabla de cache si no existe."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                provider    TEXT NOT NULL DEFAULT 'unknown',
                created_at  REAL NOT NULL,
                ttl_seconds INTEGER NOT NULL DEFAULT 3600
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_provider
            ON api_cache(provider)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_created
            ON api_cache(created_at)
        """)
        conn.commit()


def _cleanup():
    """
    Elimina entradas expiradas hace más de _STALE_RETENTION.
    Las expiradas recientes se conservan: cache_get_stale las usa como
    fallback cuando el proveedor externo no responde.
    """
    try:
        with _get_db() as conn:
            now = time.time()
            conn.execute(
                "DELETE FROM api_cache WHERE created_at + ttl_seconds + ? < ?",
                (_STALE_RETENTION, now),
            )
            conn.commit()
    except Exception as e:
        logger.warning(f"Cache cleanup error: {e}")


def cache_get(key: str) -> Optional[Any]:
    """
    Obtiene valor del cache si existe y no ha expirado.

    Args:
        key: Clave única del cache

    Returns:
        Valor deserializado o None si no existe/expiro
    """
    try:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT value, created_at, ttl_seconds FROM api_cache WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            value_json, created_at, ttl = row["value"], row["created_at"], row["ttl_seconds"]
            if time.time() - created_at < ttl:
                return json.loads(value_json)
            # Expirado: NO se borra aquí — queda disponible para cache_get_stale
            # como fallback si la API falla (lo purga _cleanup pasada la retención)
            return None
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


def cache_get_stale(key: str) -> Optional[Any]:
    """
    Obtiene valor incluso si expiro (para fallback cuando la API falla).

    Args:
        key: Clave única del cache

    Returns:
        Valor deserializado o None si no existe
    """
    try:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT value FROM api_cache WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row["value"])
    except Exception as e:
        logger.warning(f"Cache get_stale error: {e}")
        return None


def cache_set(key: str, value: Any, provider: str = "unknown", ttl_seconds: int = 3600):
    """
    Almacena un valor en el cache.

    Args:
        key: Clave única
        value: Valor a serializar (debe ser JSON-serializable)
        provider: Nombre del proveedor ('travelpayouts', 'rapidapi', 'reference')
        ttl_seconds: Tiempo de vida en segundos
    """
    try:
        with _write_lock:
            with _get_db() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO api_cache (key, value, provider, created_at, ttl_seconds)
                       VALUES (?, ?, ?, ?, ?)""",
                    (key, json.dumps(value), provider, time.time(), ttl_seconds),
                )
                conn.commit()
        # Limpieza probabilistica de expirados: 1 de cada 10 escrituras
        if random.random() < 0.1:
            _cleanup()
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


def cache_clear():
    """Limpia todas las entradas del cache."""
    try:
        with _write_lock:
            with _get_db() as conn:
                conn.execute("DELETE FROM api_cache")
                conn.commit()
    except Exception as e:
        logger.warning(f"Cache clear error: {e}")


def cache_stats() -> dict:
    """
    Estadisticas del cache.

    Returns:
        Dict con total de entradas, expiradas, y desglose por provider
    """
    try:
        with _get_db() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM api_cache").fetchone()["c"]
            expired = conn.execute(
                "SELECT COUNT(*) as c FROM api_cache WHERE created_at + ttl_seconds < ?",
                (time.time(),),
            ).fetchone()["c"]
            providers = conn.execute(
                "SELECT provider, COUNT(*) as c FROM api_cache GROUP BY provider"
            ).fetchall()
            return {
                "total": total,
                "expired": expired,
                "by_provider": {p["provider"]: p["c"] for p in providers},
            }
    except Exception as e:
        return {"error": str(e)}


# Inicializar DB al importar el modulo
_init_db()
_cleanup()
