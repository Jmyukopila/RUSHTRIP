# services/auth.py
# Logica de autenticacion: hashing de contrasenas (PBKDF2-HMAC-SHA256 de stdlib,
# sin dependencias externas) y gestion de sesiones con tokens opacos.

import hashlib
import hmac
import re
import secrets
import time

from core import auth_db
from core.errors import ValidationError

# Parametros de hashing
_ITERACIONES = 200_000
_ALGO = "sha256"

# Duracion de la sesion: 30 dias
_SESION_TTL = 30 * 24 * 3600

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Telefono: digitos, opcional prefijo +, espacios, guiones y parentesis.
_TELEFONO_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


def _hash_password(password: str, salt: str) -> str:
    """Deriva el hash PBKDF2 de la contrasena en hexadecimal."""
    dk = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), salt.encode("utf-8"), _ITERACIONES)
    return dk.hex()


def _usuario_publico(usuario: dict) -> dict:
    """Proyeccion segura del usuario (sin hash ni salt)."""
    return {
        "id":       usuario["id"],
        "email":    usuario["email"],
        "nombre":   usuario["nombre"],
        "telefono": usuario["telefono"],
        "pais":     usuario["pais"],
    }


def registrar(email: str, password: str, nombre: str = "", telefono: str = "", pais: str = "") -> dict:
    """
    Registra un usuario nuevo y devuelve {usuario, token}.
    Lanza ValidationError si el email es invalido, la contrasena es corta,
    faltan datos obligatorios (nombre, telefono, pais) o el email ya existe.
    """
    email = (email or "").strip().lower()
    nombre = (nombre or "").strip()
    telefono = (telefono or "").strip()
    pais = (pais or "").strip()

    if not _EMAIL_RE.match(email):
        raise ValidationError("Correo electronico invalido.", field="email")
    if len(password or "") < 8:
        raise ValidationError("La contrasena debe tener al menos 8 caracteres.", field="password")
    if len(nombre) < 2:
        raise ValidationError("El nombre es obligatorio.", field="nombre")
    if telefono and not _TELEFONO_RE.match(telefono):
        raise ValidationError("Numero de telefono invalido.", field="telefono")
    if len(pais) < 2:
        raise ValidationError("El pais es obligatorio.", field="pais")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    usuario_id = auth_db.crear_usuario(email, nombre, telefono, pais, password_hash, salt)
    if usuario_id is None:
        raise ValidationError("Ya existe una cuenta con este correo.", field="email")

    usuario = auth_db.obtener_usuario_por_id(usuario_id)
    token = _crear_sesion(usuario_id)
    return {"usuario": _usuario_publico(usuario), "token": token}


def iniciar_sesion(email: str, password: str) -> dict:
    """
    Autentica un usuario y devuelve {usuario, token}.
    Lanza ValidationError con mensaje generico si las credenciales fallan.
    """
    email = (email or "").strip().lower()
    usuario = auth_db.obtener_usuario_por_email(email)

    # Mensaje generico para no revelar si el email existe.
    if usuario is None:
        raise ValidationError("Correo o contrasena incorrectos.", field="credenciales")

    esperado = usuario["password_hash"]
    calculado = _hash_password(password or "", usuario["salt"])
    if not hmac.compare_digest(esperado, calculado):
        raise ValidationError("Correo o contrasena incorrectos.", field="credenciales")

    auth_db.actualizar_ultimo_acceso(usuario["id"])
    token = _crear_sesion(usuario["id"])
    return {"usuario": _usuario_publico(usuario), "token": token}


def perfil(usuario_id: int) -> dict | None:
    """
    Devuelve el perfil enriquecido del usuario: datos publicos + estadisticas
    (fecha de registro, ultimo acceso, cantidad de reservas) + destinos preferidos.
    """
    usuario = auth_db.obtener_usuario_por_id(usuario_id)
    if usuario is None:
        return None
    publico = _usuario_publico(usuario)
    publico.update({
        "reservas_count": usuario.get("reservas_count", 0),
        "fecha_registro": usuario.get("created_at"),
        "ultimo_acceso":  usuario.get("ultimo_acceso"),
        "destinos_preferidos": auth_db.listar_destinos_preferidos(usuario_id),
    })
    return publico


def registrar_reserva(usuario_id: int, datos: dict) -> int:
    """
    Guarda una reserva confirmada y refuerza el destino como preferido.
    Devuelve el id de la reserva creada.
    """
    reserva_id = auth_db.crear_reserva(usuario_id, datos)
    auth_db.registrar_destino_preferido(usuario_id, datos["destino"], datos.get("ciudad_destino", ""))
    return reserva_id


def listar_reservas(usuario_id: int) -> list[dict]:
    return auth_db.listar_reservas(usuario_id)


def registrar_destino_buscado(usuario_id: int, destino_iata: str, ciudad: str = ""):
    """Suma el destino a las preferencias del usuario (best-effort, no critico)."""
    try:
        auth_db.registrar_destino_preferido(usuario_id, destino_iata, ciudad)
    except Exception:  # noqa: BLE001 - registrar preferencias nunca debe romper el plan
        pass


def _crear_sesion(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    auth_db.guardar_sesion(token, usuario_id, time.time() + _SESION_TTL)
    return token


def cerrar_sesion(token: str):
    """Invalida un token de sesion."""
    if token:
        auth_db.borrar_sesion(token)


def usuario_de_token(token: str) -> dict | None:
    """Devuelve el usuario publico asociado a un token valido, o None."""
    if not token:
        return None
    sesion = auth_db.obtener_sesion(token)
    if sesion is None:
        return None
    usuario = auth_db.obtener_usuario_por_id(sesion["usuario_id"])
    if usuario is None:
        return None
    return _usuario_publico(usuario)
