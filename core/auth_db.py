# core/auth_db.py
# Capa de datos de usuarios con backend HIBRIDO:
#   - Si SUPABASE_DB_URL esta configurado en .env -> usa Supabase (core/supabase_db.py).
#   - Si no -> degrada a SQLite local (rushtrip_cache.db), igual que el cache/rate-limiter.
#
# Esta separacion respeta la filosofia del proyecto (cascada de fallback y "funciona
# sin credenciales"): en la nube persisten cuentas, sesiones, destinos preferidos y
# reservas; el cache/rate-limiter siempre son locales. La API publica (funciones de
# abajo) es la misma en ambos backends, asi services/auth.py no distingue cual usa.

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from core.config import settings

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).resolve().parent.parent / "cache"
_DB_PATH = _DB_DIR / "rushtrip_cache.db"


# ─── Seleccion de backend ────────────────────────────────────────────────────
# Se resuelve al importar. Si Supabase esta configurado pero falla (psycopg no
# instalado o DB inalcanzable), se cae a SQLite para no tumbar la app.
_sb = None
if settings.supabase_db_url:
    try:
        from core import supabase_db as _sb
        _sb.init_db()
        logger.info("auth_db: usando backend Supabase.")
    except Exception as e:  # noqa: BLE001 - degradar es intencional
        logger.warning("auth_db: Supabase no disponible (%s). Usando SQLite local.", e)
        _sb = None


def _usando_supabase() -> bool:
    return _sb is not None


# ─── Implementacion SQLite (fallback local) ──────────────────────────────────

def _get_db() -> sqlite3.Connection:
    """Abre conexion SQLite en WAL mode para lectura/escritura."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _sqlite_init():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                email          TEXT NOT NULL UNIQUE,
                nombre         TEXT NOT NULL DEFAULT '',
                telefono       TEXT NOT NULL DEFAULT '',
                pais           TEXT NOT NULL DEFAULT '',
                password_hash  TEXT NOT NULL,
                salt           TEXT NOT NULL,
                reservas_count INTEGER NOT NULL DEFAULT 0,
                ultimo_acceso  REAL,
                created_at     REAL NOT NULL
            )
        """)
        # Migraciones para DBs creadas antes de agregar columnas nuevas.
        columnas = {row["name"] for row in conn.execute("PRAGMA table_info(usuarios)")}
        if "telefono" not in columnas:
            conn.execute("ALTER TABLE usuarios ADD COLUMN telefono TEXT NOT NULL DEFAULT ''")
        if "pais" not in columnas:
            conn.execute("ALTER TABLE usuarios ADD COLUMN pais TEXT NOT NULL DEFAULT ''")
        if "reservas_count" not in columnas:
            conn.execute("ALTER TABLE usuarios ADD COLUMN reservas_count INTEGER NOT NULL DEFAULT 0")
        if "ultimo_acceso" not in columnas:
            conn.execute("ALTER TABLE usuarios ADD COLUMN ultimo_acceso REAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sesiones (
                token      TEXT PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sesiones_usuario ON sesiones(usuario_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS destinos_preferidos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id   INTEGER NOT NULL,
                destino_iata TEXT NOT NULL,
                ciudad       TEXT NOT NULL DEFAULT '',
                veces        INTEGER NOT NULL DEFAULT 1,
                favorito     INTEGER NOT NULL DEFAULT 0,
                ultimo_uso   REAL NOT NULL,
                created_at   REAL NOT NULL,
                UNIQUE (usuario_id, destino_iata),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservas (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id         INTEGER NOT NULL,
                origen             TEXT NOT NULL,
                destino            TEXT NOT NULL,
                fecha_salida       TEXT NOT NULL,
                fecha_regreso      TEXT NOT NULL,
                pasajeros          INTEGER NOT NULL DEFAULT 1,
                tier               TEXT NOT NULL DEFAULT 'estandar',
                presupuesto        REAL,
                total              REAL NOT NULL,
                dentro_presupuesto INTEGER NOT NULL DEFAULT 1,
                incluir_hotel      INTEGER NOT NULL DEFAULT 1,
                incluir_vehiculo   INTEGER NOT NULL DEFAULT 0,
                precision          TEXT,
                detalle            TEXT,
                estado             TEXT NOT NULL DEFAULT 'confirmada',
                created_at         REAL NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reservas_usuario ON reservas(usuario_id)")
        conn.commit()


def _sqlite_crear_usuario(email, nombre, telefono, pais, password_hash, salt) -> Optional[int]:
    try:
        with _get_db() as conn:
            cur = conn.execute(
                """INSERT INTO usuarios (email, nombre, telefono, pais, password_hash, salt, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (email, nombre, telefono, pais, password_hash, salt, time.time()),
            )
            conn.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def _sqlite_obtener_usuario_por_email(email: str) -> Optional[dict]:
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def _sqlite_obtener_usuario_por_id(usuario_id: int) -> Optional[dict]:
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return dict(row) if row else None


def _sqlite_actualizar_ultimo_acceso(usuario_id: int):
    with _get_db() as conn:
        conn.execute("UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?", (time.time(), usuario_id))
        conn.commit()


def _sqlite_guardar_sesion(token: str, usuario_id: int, expires_at: float):
    with _get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO sesiones (token, usuario_id, created_at, expires_at)
               VALUES (?, ?, ?, ?)""",
            (token, usuario_id, time.time(), expires_at),
        )
        conn.commit()


def _sqlite_obtener_sesion(token: str) -> Optional[dict]:
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM sesiones WHERE token = ?", (token,)).fetchone()
        if row is None:
            return None
        if row["expires_at"] < time.time():
            conn.execute("DELETE FROM sesiones WHERE token = ?", (token,))
            conn.commit()
            return None
        return dict(row)


def _sqlite_borrar_sesion(token: str):
    with _get_db() as conn:
        conn.execute("DELETE FROM sesiones WHERE token = ?", (token,))
        conn.commit()


def _sqlite_registrar_destino_preferido(usuario_id: int, destino_iata: str, ciudad: str = ""):
    ahora = time.time()
    with _get_db() as conn:
        conn.execute(
            """INSERT INTO destinos_preferidos (usuario_id, destino_iata, ciudad, ultimo_uso, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (usuario_id, destino_iata) DO UPDATE
                 SET veces = veces + 1,
                     ultimo_uso = excluded.ultimo_uso,
                     ciudad = CASE WHEN excluded.ciudad != '' THEN excluded.ciudad ELSE ciudad END""",
            (usuario_id, destino_iata, ciudad, ahora, ahora),
        )
        conn.commit()


def _sqlite_listar_destinos_preferidos(usuario_id: int, limite: int = 10) -> list[dict]:
    with _get_db() as conn:
        rows = conn.execute(
            """SELECT destino_iata, ciudad, veces, favorito, ultimo_uso
               FROM destinos_preferidos WHERE usuario_id = ?
               ORDER BY favorito DESC, veces DESC, ultimo_uso DESC LIMIT ?""",
            (usuario_id, limite),
        ).fetchall()
        return [dict(r) for r in rows]


def _sqlite_crear_reserva(usuario_id: int, datos: dict) -> int:
    detalle = json.dumps(datos.get("detalle"), ensure_ascii=False) if datos.get("detalle") is not None else None
    with _get_db() as conn:
        cur = conn.execute(
            """INSERT INTO reservas
                 (usuario_id, origen, destino, fecha_salida, fecha_regreso, pasajeros, tier,
                  presupuesto, total, dentro_presupuesto, incluir_hotel, incluir_vehiculo,
                  precision, detalle, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                usuario_id, datos["origen"], datos["destino"],
                datos["fecha_salida"], datos["fecha_regreso"],
                datos.get("pasajeros", 1), datos.get("tier", "estandar"),
                datos.get("presupuesto"), datos["total"],
                1 if datos.get("dentro_presupuesto", True) else 0,
                1 if datos.get("incluir_hotel", True) else 0,
                1 if datos.get("incluir_vehiculo", False) else 0,
                datos.get("precision"), detalle, time.time(),
            ),
        )
        # SQLite no tiene el trigger de Supabase: mantener el contador aqui.
        conn.execute("UPDATE usuarios SET reservas_count = reservas_count + 1 WHERE id = ?", (usuario_id,))
        conn.commit()
        return cur.lastrowid


def _sqlite_listar_reservas(usuario_id: int, limite: int = 50) -> list[dict]:
    with _get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM reservas WHERE usuario_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (usuario_id, limite),
        ).fetchall()
        resultado = []
        for r in rows:
            d = dict(r)
            if d.get("detalle"):
                try:
                    d["detalle"] = json.loads(d["detalle"])
                except (ValueError, TypeError):
                    pass
            resultado.append(d)
        return resultado


# ─── API publica (dispatcher hibrido) ────────────────────────────────────────

def init_db():
    """Inicializa el backend activo. Llamado al startup desde main.py."""
    if _usando_supabase():
        return  # supabase_db.init_db() ya corrio en el import
    _sqlite_init()


def crear_usuario(email, nombre, telefono, pais, password_hash, salt) -> Optional[int]:
    if _usando_supabase():
        return _sb.crear_usuario(email, nombre, telefono, pais, password_hash, salt)
    return _sqlite_crear_usuario(email, nombre, telefono, pais, password_hash, salt)


def obtener_usuario_por_email(email: str) -> Optional[dict]:
    if _usando_supabase():
        return _sb.obtener_usuario_por_email(email)
    return _sqlite_obtener_usuario_por_email(email)


def obtener_usuario_por_id(usuario_id: int) -> Optional[dict]:
    if _usando_supabase():
        return _sb.obtener_usuario_por_id(usuario_id)
    return _sqlite_obtener_usuario_por_id(usuario_id)


def actualizar_ultimo_acceso(usuario_id: int):
    if _usando_supabase():
        return _sb.actualizar_ultimo_acceso(usuario_id)
    return _sqlite_actualizar_ultimo_acceso(usuario_id)


def guardar_sesion(token: str, usuario_id: int, expires_at: float):
    if _usando_supabase():
        return _sb.guardar_sesion(token, usuario_id, expires_at)
    return _sqlite_guardar_sesion(token, usuario_id, expires_at)


def obtener_sesion(token: str) -> Optional[dict]:
    if _usando_supabase():
        return _sb.obtener_sesion(token)
    return _sqlite_obtener_sesion(token)


def borrar_sesion(token: str):
    if _usando_supabase():
        return _sb.borrar_sesion(token)
    return _sqlite_borrar_sesion(token)


def registrar_destino_preferido(usuario_id: int, destino_iata: str, ciudad: str = ""):
    if _usando_supabase():
        return _sb.registrar_destino_preferido(usuario_id, destino_iata, ciudad)
    return _sqlite_registrar_destino_preferido(usuario_id, destino_iata, ciudad)


def listar_destinos_preferidos(usuario_id: int, limite: int = 10) -> list[dict]:
    if _usando_supabase():
        return _sb.listar_destinos_preferidos(usuario_id, limite)
    return _sqlite_listar_destinos_preferidos(usuario_id, limite)


def crear_reserva(usuario_id: int, datos: dict) -> int:
    if _usando_supabase():
        return _sb.crear_reserva(usuario_id, datos)
    return _sqlite_crear_reserva(usuario_id, datos)


def listar_reservas(usuario_id: int, limite: int = 50) -> list[dict]:
    if _usando_supabase():
        return _sb.listar_reservas(usuario_id, limite)
    return _sqlite_listar_reservas(usuario_id, limite)


# Inicializar el backend SQLite al importar (no-op si se usa Supabase).
if not _usando_supabase():
    _sqlite_init()
