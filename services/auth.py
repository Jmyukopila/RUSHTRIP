# services/auth.py
# Logica de autenticacion: hashing de contrasenas (PBKDF2-HMAC-SHA256 de stdlib,
# sin dependencias externas) y gestion de sesiones con tokens opacos.

import hashlib
import hmac
import logging
import re
import secrets
import time

from core import auth_db
from core import email as correo
from core.config import settings
from core.errors import RateLimitError, ValidationError

logger = logging.getLogger(__name__)

# Parametros de hashing
_ITERACIONES = 200_000
_ALGO = "sha256"

# Duracion de la sesion: 30 dias
_SESION_TTL = 30 * 24 * 3600

# Vigencia de los tokens de un solo uso enviados por correo.
_TTL_RESET = 60 * 60           # recuperacion de contrasena: 1 hora
_TTL_VERIFICACION = 24 * 3600  # verificacion de email: 24 horas

# ─── Proteccion contra fuerza bruta por cuenta ──────────────────────────────
# Complementa el rate limit por IP: frena ataques distribuidos contra UNA cuenta.
# Contadores en memoria por proceso (mismo alcance que los throttles de
# core/http.py); con varios workers el limite efectivo se multiplica, pero el
# backoff exponencial sigue haciendo inviable la fuerza bruta.
_MAX_INTENTOS_LIBRES = 5     # fallos consecutivos permitidos antes de bloquear
_BLOQUEO_BASE = 30           # segundos del primer bloqueo
_BLOQUEO_MAX = 15 * 60       # tope del backoff exponencial
_INTENTOS: dict[str, dict] = {}  # email -> {fallos, bloqueado_hasta, ultimo}


def _segundos_bloqueo(fallos: int) -> float:
    """Backoff exponencial: 30s en el 5.o fallo, duplicando hasta 15 min."""
    exceso = fallos - _MAX_INTENTOS_LIBRES
    return min(_BLOQUEO_BASE * (2 ** exceso), _BLOQUEO_MAX)


def _verificar_bloqueo(email: str):
    """Lanza RateLimitError si la cuenta esta temporalmente bloqueada."""
    entrada = _INTENTOS.get(email)
    if not entrada:
        return
    restante = entrada.get("bloqueado_hasta", 0.0) - time.time()
    if restante <= 0:
        return
    minutos = int(restante // 60)
    espera = (
        f"{minutos} minuto{'s' if minutos != 1 else ''}"
        if minutos >= 1
        else f"{max(int(restante), 1)} segundos"
    )
    raise RateLimitError(
        f"Demasiados intentos fallidos con esta cuenta. Intenta de nuevo en {espera}."
    )


def _registrar_fallo(email: str):
    ahora = time.time()
    # Poda contadores viejos para que el dict no crezca sin limite.
    if len(_INTENTOS) > 1000:
        vencidos = [k for k, v in _INTENTOS.items() if ahora - v.get("ultimo", 0) > 3600]
        for k in vencidos:
            _INTENTOS.pop(k, None)
    entrada = _INTENTOS.setdefault(email, {"fallos": 0, "bloqueado_hasta": 0.0, "ultimo": ahora})
    entrada["fallos"] += 1
    entrada["ultimo"] = ahora
    if entrada["fallos"] >= _MAX_INTENTOS_LIBRES:
        entrada["bloqueado_hasta"] = ahora + _segundos_bloqueo(entrada["fallos"])


def _limpiar_fallos(email: str):
    _INTENTOS.pop(email, None)

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
        # SQLite guarda 0/1; Supabase, booleano. Normalizamos a bool para el frontend.
        "email_verificado": bool(usuario.get("email_verificado", False)),
    }


def registrar(
    email: str, password: str, nombre: str = "", telefono: str = "", pais: str = "",
    acepta_terminos: bool = False,
) -> dict:
    """
    Registra un usuario nuevo y devuelve {usuario, token}.
    Lanza ValidationError si el email es invalido, la contrasena es corta,
    faltan datos obligatorios (nombre, telefono, pais), no se aceptaron los
    terminos o el email ya existe.
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
    # Consentimiento explicito: la fuente de verdad es el servidor, no el checkbox
    # del navegador (trivial de saltear). Guardamos ademas cuando se acepto.
    if not acepta_terminos:
        raise ValidationError(
            "Debes aceptar los Terminos de Servicio y la Politica de Privacidad.",
            field="acepta_terminos",
        )

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    usuario_id = auth_db.crear_usuario(
        email, nombre, telefono, pais, password_hash, salt,
        terminos_aceptados_at=time.time(),
    )
    if usuario_id is None:
        raise ValidationError("Ya existe una cuenta con este correo.", field="email")

    usuario = auth_db.obtener_usuario_por_id(usuario_id)
    _enviar_verificacion(usuario)  # best-effort: no bloquea el registro
    token = _crear_sesion(usuario_id)
    return {"usuario": _usuario_publico(usuario), "token": token}


# ─── Verificacion de email y recuperacion de contrasena ─────────────────────

def _enviar_verificacion(usuario: dict):
    """
    Genera un token de verificacion y envia (o registra en el log, en dev) el
    enlace. Best-effort: nunca lanza, para no romper el registro si el correo falla.
    """
    try:
        auth_db.borrar_tokens_usuario(usuario["id"], "verificacion")
        token = secrets.token_urlsafe(32)
        auth_db.crear_token(token, usuario["id"], "verificacion", time.time() + _TTL_VERIFICACION)
        enlace = f"{settings.app_base_url.rstrip('/')}/verificar-email?token={token}"
        correo.enviar_email(
            usuario["email"],
            "Verifica tu correo en RushTrip",
            f"Hola {usuario.get('nombre', '')}:\n\n"
            f"Confirma tu correo entrando a este enlace (vence en 24 horas):\n{enlace}\n\n"
            "Si no creaste esta cuenta, ignora este mensaje.",
        )
    except Exception:  # noqa: BLE001 - enviar el correo nunca debe romper el flujo
        logger.warning("No se pudo generar/enviar la verificacion de email.", exc_info=True)


def solicitar_reset(email: str) -> dict:
    """
    Inicia la recuperacion de contrasena: si el correo existe, envia un enlace.
    La respuesta es SIEMPRE generica para no revelar si el correo esta registrado.
    """
    email = (email or "").strip().lower()
    usuario = auth_db.obtener_usuario_por_email(email) if _EMAIL_RE.match(email) else None
    if usuario is not None:
        try:
            auth_db.borrar_tokens_usuario(usuario["id"], "reset")
            token = secrets.token_urlsafe(32)
            auth_db.crear_token(token, usuario["id"], "reset", time.time() + _TTL_RESET)
            enlace = f"{settings.app_base_url.rstrip('/')}/reset-password?token={token}"
            correo.enviar_email(
                usuario["email"],
                "Restablece tu contrasena en RushTrip",
                f"Hola {usuario.get('nombre', '')}:\n\n"
                f"Para elegir una contrasena nueva entra aqui (vence en 1 hora):\n{enlace}\n\n"
                "Si no pediste este cambio, ignora este mensaje: tu contrasena sigue igual.",
            )
        except Exception:  # noqa: BLE001 - no filtrar errores al usuario
            logger.warning("No se pudo generar/enviar el reset de contrasena.", exc_info=True)
    return {
        "ok": True,
        "mensaje": "Si el correo esta registrado, te enviamos un enlace para restablecer tu contrasena.",
    }


def resetear_password(token: str, nueva_password: str) -> dict:
    """
    Cambia la contrasena a partir de un token de reset valido.
    Lanza ValidationError si la contrasena es corta o el token es invalido/expiro.
    """
    if len(nueva_password or "") < 8:
        raise ValidationError("La contrasena debe tener al menos 8 caracteres.", field="password")

    registro = auth_db.obtener_token((token or "").strip(), "reset")
    if registro is None:
        raise ValidationError("El enlace de recuperacion es invalido o ha expirado.", field="token")

    usuario_id = registro["usuario_id"]
    salt = secrets.token_hex(16)
    auth_db.actualizar_password(usuario_id, _hash_password(nueva_password, salt), salt)
    auth_db.borrar_tokens_usuario(usuario_id, "reset")
    # Seguridad: cierra todas las sesiones abiertas y limpia el backoff de la cuenta.
    auth_db.borrar_sesiones_usuario(usuario_id)
    usuario = auth_db.obtener_usuario_por_id(usuario_id)
    if usuario:
        _limpiar_fallos(usuario["email"])
    return {"ok": True}


def verificar_email(token: str) -> dict:
    """Marca el email como verificado a partir de un token valido."""
    registro = auth_db.obtener_token((token or "").strip(), "verificacion")
    if registro is None:
        raise ValidationError("El enlace de verificacion es invalido o ha expirado.", field="token")
    auth_db.marcar_email_verificado(registro["usuario_id"])
    auth_db.borrar_token(token)
    usuario = auth_db.obtener_usuario_por_id(registro["usuario_id"])
    return {"ok": True, "usuario": _usuario_publico(usuario) if usuario else None}


def reenviar_verificacion(usuario_id: int) -> dict:
    """Reenvia el correo de verificacion si la cuenta aun no esta verificada."""
    usuario = auth_db.obtener_usuario_por_id(usuario_id)
    if usuario and not usuario.get("email_verificado"):
        _enviar_verificacion(usuario)
    return {"ok": True}


def iniciar_sesion(email: str, password: str) -> dict:
    """
    Autentica un usuario y devuelve {usuario, token}.
    Lanza ValidationError con mensaje generico si las credenciales fallan y
    RateLimitError si la cuenta acumulo demasiados intentos fallidos seguidos.
    """
    email = (email or "").strip().lower()
    # Los fallos se cuentan aunque el email no exista, para no revelar
    # que cuentas estan registradas midiendo cuando aparece el bloqueo.
    _verificar_bloqueo(email)
    usuario = auth_db.obtener_usuario_por_email(email)

    # Mensaje generico para no revelar si el email existe.
    if usuario is None:
        _registrar_fallo(email)
        raise ValidationError("Correo o contrasena incorrectos.", field="credenciales")

    esperado = usuario["password_hash"]
    calculado = _hash_password(password or "", usuario["salt"])
    if not hmac.compare_digest(esperado, calculado):
        _registrar_fallo(email)
        raise ValidationError("Correo o contrasena incorrectos.", field="credenciales")

    _limpiar_fallos(email)
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
