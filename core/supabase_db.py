# core/supabase_db.py
# Backend de datos de usuarios sobre Supabase (Postgres) usando psycopg.
# Es la mitad "nube" del almacenamiento hibrido: cuentas, sesiones, destinos
# preferidos y reservas viven aqui; el cache/rate-limiter siguen en SQLite.
#
# Se activa cuando SUPABASE_DB_URL esta configurado en .env. Si no, core/auth_db
# degrada a SQLite local (ver core/auth_db.py). Toda la DDL es idempotente para
# que apuntar a una DB nueva funcione sin pasos manuales.

import logging
from datetime import datetime, timezone
from typing import Optional

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from core.config import settings

logger = logging.getLogger(__name__)


def _conn() -> psycopg.Connection:
    """Abre una conexion a Supabase con filas como dict."""
    return psycopg.connect(settings.supabase_db_url, row_factory=dict_row, connect_timeout=10)


def _ts(epoch: float) -> datetime:
    """Convierte epoch (segundos) a datetime UTC para columnas TIMESTAMPTZ."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def init_db():
    """
    Crea las tablas si no existen (idempotente). En el proyecto ya se crearon via
    migracion, pero esto permite apuntar a un Postgres nuevo sin pasos manuales.
    """
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public.usuarios (
                id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                email          TEXT NOT NULL UNIQUE,
                nombre         TEXT NOT NULL DEFAULT '',
                telefono       TEXT NOT NULL DEFAULT '',
                pais           TEXT NOT NULL DEFAULT '',
                password_hash  TEXT NOT NULL,
                salt           TEXT NOT NULL,
                reservas_count INTEGER NOT NULL DEFAULT 0,
                ultimo_acceso  TIMESTAMPTZ,
                terminos_aceptados_at TIMESTAMPTZ,
                email_verificado BOOLEAN NOT NULL DEFAULT false,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        # Migraciones idempotentes para DBs creadas antes de agregar columnas.
        conn.execute(
            "ALTER TABLE public.usuarios "
            "ADD COLUMN IF NOT EXISTS terminos_aceptados_at TIMESTAMPTZ"
        )
        conn.execute(
            "ALTER TABLE public.usuarios "
            "ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN NOT NULL DEFAULT false"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public.tokens_auth (
                token      TEXT PRIMARY KEY,
                usuario_id BIGINT NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
                tipo       TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tokens_usuario "
            "ON public.tokens_auth(usuario_id, tipo)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public.sesiones (
                token      TEXT PRIMARY KEY,
                usuario_id BIGINT NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at TIMESTAMPTZ NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public.destinos_preferidos (
                id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                usuario_id   BIGINT NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
                destino_iata TEXT NOT NULL,
                ciudad       TEXT NOT NULL DEFAULT '',
                veces        INTEGER NOT NULL DEFAULT 1,
                favorito     BOOLEAN NOT NULL DEFAULT false,
                ultimo_uso   TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (usuario_id, destino_iata)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS public.reservas (
                id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                usuario_id         BIGINT NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
                origen             TEXT NOT NULL,
                destino            TEXT NOT NULL,
                fecha_salida       DATE NOT NULL,
                fecha_regreso      DATE NOT NULL,
                pasajeros          INTEGER NOT NULL DEFAULT 1,
                tier               TEXT NOT NULL DEFAULT 'estandar',
                presupuesto        NUMERIC(12,2),
                total              NUMERIC(12,2) NOT NULL,
                dentro_presupuesto BOOLEAN NOT NULL DEFAULT true,
                incluir_hotel      BOOLEAN NOT NULL DEFAULT true,
                incluir_vehiculo   BOOLEAN NOT NULL DEFAULT false,
                precision          TEXT,
                detalle            JSONB,
                estado             TEXT NOT NULL DEFAULT 'confirmada',
                created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        conn.commit()
    logger.info("Supabase: tablas de usuarios verificadas.")


# ─── Usuarios ──────────────────────────────────────────────────────────────

def crear_usuario(email, nombre, telefono, pais, password_hash, salt,
                  terminos_aceptados_at=None) -> Optional[int]:
    """Inserta un usuario nuevo. Devuelve su id, o None si el email ya existe."""
    try:
        with _conn() as conn:
            row = conn.execute(
                """INSERT INTO public.usuarios
                     (email, nombre, telefono, pais, password_hash, salt, terminos_aceptados_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (email, nombre, telefono, pais, password_hash, salt,
                 _ts(terminos_aceptados_at) if terminos_aceptados_at is not None else None),
            ).fetchone()
            conn.commit()
            return row["id"]
    except psycopg.errors.UniqueViolation:
        return None


def obtener_usuario_por_email(email: str) -> Optional[dict]:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM public.usuarios WHERE email = %s", (email,)
        ).fetchone()


def obtener_usuario_por_id(usuario_id: int) -> Optional[dict]:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM public.usuarios WHERE id = %s", (usuario_id,)
        ).fetchone()


def actualizar_ultimo_acceso(usuario_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE public.usuarios SET ultimo_acceso = now() WHERE id = %s", (usuario_id,)
        )
        conn.commit()


def actualizar_password(usuario_id: int, password_hash: str, salt: str):
    with _conn() as conn:
        conn.execute(
            "UPDATE public.usuarios SET password_hash = %s, salt = %s WHERE id = %s",
            (password_hash, salt, usuario_id),
        )
        conn.commit()


def marcar_email_verificado(usuario_id: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE public.usuarios SET email_verificado = true WHERE id = %s", (usuario_id,)
        )
        conn.commit()


# ─── Tokens de un solo uso (reset de contrasena / verificacion de email) ────

def crear_token(token: str, usuario_id: int, tipo: str, expires_at: float):
    with _conn() as conn:
        conn.execute(
            """INSERT INTO public.tokens_auth (token, usuario_id, tipo, expires_at)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (token) DO UPDATE
                 SET usuario_id = EXCLUDED.usuario_id, tipo = EXCLUDED.tipo,
                     expires_at = EXCLUDED.expires_at""",
            (token, usuario_id, tipo, _ts(expires_at)),
        )
        conn.commit()


def obtener_token(token: str, tipo: str) -> Optional[dict]:
    """Devuelve el token si existe, es del tipo dado y no ha expirado. Purga los vencidos."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT token, usuario_id, tipo, expires_at FROM public.tokens_auth "
            "WHERE token = %s AND tipo = %s",
            (token, tipo),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < datetime.now(timezone.utc):
            conn.execute("DELETE FROM public.tokens_auth WHERE token = %s", (token,))
            conn.commit()
            return None
        return row


def borrar_token(token: str):
    with _conn() as conn:
        conn.execute("DELETE FROM public.tokens_auth WHERE token = %s", (token,))
        conn.commit()


def borrar_tokens_usuario(usuario_id: int, tipo: str):
    with _conn() as conn:
        conn.execute(
            "DELETE FROM public.tokens_auth WHERE usuario_id = %s AND tipo = %s",
            (usuario_id, tipo),
        )
        conn.commit()


# ─── Sesiones ──────────────────────────────────────────────────────────────

def guardar_sesion(token: str, usuario_id: int, expires_at: float):
    with _conn() as conn:
        conn.execute(
            """INSERT INTO public.sesiones (token, usuario_id, expires_at)
               VALUES (%s, %s, %s)
               ON CONFLICT (token) DO UPDATE
                 SET usuario_id = EXCLUDED.usuario_id, expires_at = EXCLUDED.expires_at""",
            (token, usuario_id, _ts(expires_at)),
        )
        conn.commit()


def obtener_sesion(token: str) -> Optional[dict]:
    """Devuelve la sesion si existe y no ha expirado. Purga las vencidas."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT token, usuario_id, expires_at FROM public.sesiones WHERE token = %s",
            (token,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < datetime.now(timezone.utc):
            conn.execute("DELETE FROM public.sesiones WHERE token = %s", (token,))
            conn.commit()
            return None
        return row


def borrar_sesion(token: str):
    with _conn() as conn:
        conn.execute("DELETE FROM public.sesiones WHERE token = %s", (token,))
        conn.commit()


def borrar_sesiones_usuario(usuario_id: int):
    """Cierra todas las sesiones de un usuario (usado al resetear la contrasena)."""
    with _conn() as conn:
        conn.execute("DELETE FROM public.sesiones WHERE usuario_id = %s", (usuario_id,))
        conn.commit()


# ─── Destinos preferidos ───────────────────────────────────────────────────

def registrar_destino_preferido(usuario_id: int, destino_iata: str, ciudad: str = ""):
    """Suma +1 al destino (o lo crea) para construir las preferencias del usuario."""
    with _conn() as conn:
        conn.execute(
            """INSERT INTO public.destinos_preferidos (usuario_id, destino_iata, ciudad)
               VALUES (%s, %s, %s)
               ON CONFLICT (usuario_id, destino_iata) DO UPDATE
                 SET veces = public.destinos_preferidos.veces + 1,
                     ultimo_uso = now(),
                     ciudad = COALESCE(NULLIF(EXCLUDED.ciudad, ''), public.destinos_preferidos.ciudad)""",
            (usuario_id, destino_iata, ciudad),
        )
        conn.commit()


def listar_destinos_preferidos(usuario_id: int, limite: int = 10) -> list[dict]:
    with _conn() as conn:
        return conn.execute(
            """SELECT destino_iata, ciudad, veces, favorito, ultimo_uso
               FROM public.destinos_preferidos
               WHERE usuario_id = %s
               ORDER BY favorito DESC, veces DESC, ultimo_uso DESC
               LIMIT %s""",
            (usuario_id, limite),
        ).fetchall()


# ─── Reservas ──────────────────────────────────────────────────────────────

def crear_reserva(usuario_id: int, datos: dict) -> int:
    """Inserta una reserva. El trigger sync_reservas_count actualiza usuarios.reservas_count."""
    with _conn() as conn:
        row = conn.execute(
            """INSERT INTO public.reservas
                 (usuario_id, origen, destino, fecha_salida, fecha_regreso, pasajeros,
                  tier, presupuesto, total, dentro_presupuesto, incluir_hotel,
                  incluir_vehiculo, precision, detalle)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                usuario_id,
                datos["origen"], datos["destino"],
                datos["fecha_salida"], datos["fecha_regreso"],
                datos.get("pasajeros", 1), datos.get("tier", "estandar"),
                datos.get("presupuesto"), datos["total"],
                datos.get("dentro_presupuesto", True),
                datos.get("incluir_hotel", True), datos.get("incluir_vehiculo", False),
                datos.get("precision"),
                Json(datos.get("detalle")) if datos.get("detalle") is not None else None,
            ),
        ).fetchone()
        conn.commit()
        return row["id"]


def listar_reservas(usuario_id: int, limite: int = 50) -> list[dict]:
    with _conn() as conn:
        return conn.execute(
            """SELECT id, origen, destino, fecha_salida, fecha_regreso, pasajeros, tier,
                      presupuesto, total, dentro_presupuesto, incluir_hotel,
                      incluir_vehiculo, precision, detalle, estado, created_at
               FROM public.reservas
               WHERE usuario_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (usuario_id, limite),
        ).fetchall()
