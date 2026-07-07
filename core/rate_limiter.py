# core/rate_limiter.py
# Rate limiter por IP usando SQLite persistente
# Límites diarios que sobreviven reinicios del servidor

import logging
import sqlite3
import time
from datetime import date, datetime, timedelta
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
    "transport": 100,
    "hotels": 100,
    "cars": 100,
    # El autocomplete se dispara por tecleo del usuario: necesita margen amplio
    "airports": 500,
    "weather": 100,
    "activities": 100,
    "auth": 50,
    "default": 200,
}

_API_PREFIXES = ("/plan", "/flights", "/transport", "/hotels", "/cars", "/airports", "/weather", "/activities", "/auth")


def normalizar_path(path: str) -> str:
    """
    Quita el prefijo /api si está presente. El middleware de rate limit corre
    ANTES del strip de /api (es el más externo), así que en producción los
    paths llegan como /api/plan y sin normalizar caerían todos en 'default'.
    """
    if path.startswith("/api/"):
        return path[4:]
    if path == "/api":
        return "/"
    return path


def es_ruta_api(path: str) -> bool:
    """True si el path (con o sin prefijo /api) corresponde a un endpoint de la API."""
    return normalizar_path(path).startswith(_API_PREFIXES)


def ip_cliente(forwarded_for: Optional[str], fallback: str) -> str:
    """
    Extrae la IP real del cliente desde X-Forwarded-For (primer salto).
    Detrás de un proxy (Vercel, nginx) request.client.host es la IP del proxy:
    sin esto, todos los usuarios compartirían el mismo bucket de rate limit.
    """
    if forwarded_for:
        primera = forwarded_for.split(",")[0].strip()
        if primera:
            return primera
    return fallback


def segundos_hasta_reinicio() -> int:
    """Segundos hasta la próxima medianoche local (cuando se reinician los contadores)."""
    ahora = datetime.now()
    manana = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((manana - ahora).total_seconds()), 60)


def _endpoint_group(path: str) -> str:
    """Agrupa rutas en categorías de límite."""
    path = normalizar_path(path)
    for prefix in _API_PREFIXES:
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
