# core/rate_limiter.py
# Rate limiter por IP usando SQLite persistente
# Límites diarios que sobreviven reinicios del servidor

import logging
import sqlite3
import time
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).resolve().parent.parent / "cache"
_DB_PATH = _DB_DIR / "rushtrip_cache.db"


def _get_db() -> sqlite3.Connection:
    Path(_DB_DIR).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """Inicializa la base de datos del rate limiter. Llama al startup."""
    _init_db()


def _init_db():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                ip       TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                date     TEXT NOT NULL,
                count    INTEGER DEFAULT 1,
                PRIMARY KEY (ip, endpoint, date)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rate_ip_date
            ON rate_limits(ip, date)
        """)
        conn.commit()


# Límites por endpoint (requests/día/IP)
LIMITS: dict[str, int] = {
    "plan": 30,
    "flights": 100,
    "hotels": 100,
    "cars": 100,
    "airports": 100,
    "default": 200,
}


def _endpoint_group(path: str) -> str:
    """Agrupa rutas en categorías de límite."""
    for prefix in ("/plan", "/flights", "/hotels", "/cars", "/airports"):
        if path.startswith(prefix):
            return prefix.lstrip("/")
    return "default"


def check_rate_limit(ip: str, path: str) -> tuple[bool, Optional[int]]:
    """
    Verifica si una IP ha excedido el límite diario para un endpoint.

    Args:
        ip: Dirección IP del cliente
        path: Ruta de la request (ej: /plan/)

    Returns:
        Tupla (permitido: bool, limite: int | None)
        Si no permitido, limite es el máximo diario
    """
    today = date.today().isoformat()
    group = _endpoint_group(path)
    limit = LIMITS.get(group, LIMITS["default"])

    try:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT count FROM rate_limits WHERE ip = ? AND endpoint = ? AND date = ?",
                (ip, group, today),
            ).fetchone()

            if row is None:
                # Primera request del día
                conn.execute(
                    "INSERT INTO rate_limits (ip, endpoint, date, count) VALUES (?, ?, ?, 1)",
                    (ip, group, today),
                )
                conn.commit()
                return True, None

            current = row["count"]
            if current >= limit:
                logger.info(f"Rate limit exceeded: {ip} on {group} ({current}/{limit})")
                return False, limit

            # Incrementar contador
            conn.execute(
                "UPDATE rate_limits SET count = count + 1 WHERE ip = ? AND endpoint = ? AND date = ?",
                (ip, group, today),
            )
            conn.commit()
            return True, None

    except Exception as e:
        logger.warning(f"Rate limit check error: {e}")
        return True, None  # Permitir en caso de error


def get_remaining(ip: str, path: str) -> tuple[int, int]:
    """
    Obtiene el límite y las requests restantes para una IP.

    Args:
        ip: Dirección IP
        path: Ruta de la request

    Returns:
        Tupla (remaining, limit)
    """
    today = date.today().isoformat()
    group = _endpoint_group(path)
    limit = LIMITS.get(group, LIMITS["default"])

    try:
        with _get_db() as conn:
            row = conn.execute(
                "SELECT count FROM rate_limits WHERE ip = ? AND endpoint = ? AND date = ?",
                (ip, group, today),
            ).fetchone()
            used = row["count"] if row else 0
            return max(0, limit - used), limit
    except Exception:
        return limit, limit


# Inicializar DB al importar
_init_db()
