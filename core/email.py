# core/email.py
# Envio de email con degradacion, coherente con la filosofia del proyecto
# ("funciona sin credenciales"): si SMTP esta configurado en .env se envia via
# smtplib; si no (desarrollo), el correo se registra en el log y el flujo sigue.
# enviar_email nunca lanza: un fallo de correo no debe romper el flujo de auth.

import logging
import smtplib
from email.message import EmailMessage

from core.config import settings

logger = logging.getLogger(__name__)


def smtp_configurado() -> bool:
    """True si hay credenciales SMTP suficientes para enviar de verdad."""
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def enviar_email(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """
    Envia un email de texto plano. Devuelve True si se entrego al servidor SMTP.
    Sin SMTP configurado, registra el contenido en el log (util en desarrollo:
    el enlace queda visible en la consola) y devuelve False.
    """
    if not smtp_configurado():
        logger.info("[email:dev] Para: %s | Asunto: %s\n%s", destinatario, asunto, cuerpo)
        return False
    try:
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = destinatario
        msg["Subject"] = asunto
        msg.set_content(cuerpo)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001 - el correo nunca debe romper el flujo
        logger.warning("No se pudo enviar email a %s: %s", destinatario, e)
        return False
