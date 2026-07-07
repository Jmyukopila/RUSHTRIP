# core/config.py
# Configuración centralizada usando Pydantic Settings
# Soporta múltiples API keys para rotación automática

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Configuración de la aplicación extraída del archivo .env.

    Soporta múltiples keys para rotación:
      TRAVELPAYOUTS_TOKEN_1, TRAVELPAYOUTS_TOKEN_2, ...
      RAPIDAPI_KEY_1, RAPIDAPI_KEY_2, ...
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    travelpayouts_token:    str = ""
    travelpayouts_token_2:  str = ""
    travelpayouts_token_3:  str = ""
    travelpayouts_marker:   str = ""

    # Prefijo del link de afiliado de Travelpayouts para hoteles (programa por decidir).
    # Es el link generado en tu panel de Travelpayouts SIN el parametro final `&u=...`,
    # p.ej: https://tp.media/r?marker=723238&trs=<proj>&p=<prog>&campaign_id=<camp>
    # En runtime se le agrega `&u=<url-del-hotel>` para deep-linkear a cada hotel.
    # VACIO (default en desarrollo) => el boton cae a Booking.com directo, sin afiliacion.
    # Se activa al ir a produccion, cuando el sitio este en vivo y aprobado por un programa.
    travelpayouts_hotel_link: str = ""

    rapidapi_key:         str = ""
    rapidapi_key_2:       str = ""
    rapidapi_key_3:       str = ""
    rapidapi_host:        str = "booking-com15.p.rapidapi.com"

    pexels_api_key:       str = ""

    hotelsnl_api_key:     str = ""

    opentripmap_api_key:  str = ""

    # ─── DeepL (traducción de descripciones de actividades) ────────────
    deepl_api_key:        str = ""
    deepl_api_url:        str = "https://api-free.deepl.com/v2/translate"

    # ─── Supabase (backend en la nube para usuarios/sesiones/reservas) ──
    # Connection string de Postgres (usar el pooler de Supabase). Si esta VACIO,
    # la capa de usuarios degrada a SQLite local (ver core/auth_db.py).
    supabase_db_url:      str = ""
    # URL del proyecto (informativa / para integraciones futuras del frontend).
    supabase_url:         str = ""

    # ─── Envio de email (recuperacion de contrasena y verificacion) ──
    # Si SMTP no esta configurado, los correos se registran en el log (dev) en
    # vez de enviarse: el flujo funciona sin credenciales, igual que el resto.
    smtp_host:      str = ""
    smtp_port:      int = 587
    smtp_user:      str = ""
    smtp_password:  str = ""
    email_from:     str = "RushTrip <rushtripsupport@gmail.com>"
    # URL publica del frontend, para construir los enlaces de los correos.
    app_base_url:   str = "http://localhost:5173"

    cors_origins:         str = "*"
    debug:                bool = True

    @property
    def travelpayouts_tokens(self) -> List[str]:
        """Retorna todas las keys de Travelpayouts disponibles."""
        candidatos = [self.travelpayouts_token, self.travelpayouts_token_2, self.travelpayouts_token_3]
        return [t for t in candidatos if t]

    @property
    def rapidapi_keys(self) -> List[str]:
        """Retorna todas las keys de RapidAPI disponibles."""
        candidatos = [self.rapidapi_key, self.rapidapi_key_2, self.rapidapi_key_3]
        return [k for k in candidatos if k]


settings = Settings()
