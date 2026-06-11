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

    travelpayouts_token:  str = ""
    travelpayouts_marker: str = ""

    rapidapi_key:         str = ""
    rapidapi_host:        str = "booking-com15.p.rapidapi.com"

    pexels_api_key:       str = ""

    hotelsnl_api_key:     str = ""

    opentripmap_api_key:  str = ""

    cors_origins:         str = "*"
    debug:                bool = True

    @property
    def travelpayouts_tokens(self) -> List[str]:
        """Retorna todas las keys de Travelpayouts disponibles."""
        tokens = []
        if self.travelpayouts_token:
            tokens.append(self.travelpayouts_token)
        for i in range(2, 10):
            key = getattr(self, f"travelpayouts_token_{i}", None) or \
                  getattr(self, f"travelpayouts_token_{i}", "")
            if key:
                tokens.append(key)
        return tokens

    @property
    def rapidapi_keys(self) -> List[str]:
        """Retorna todas las keys de RapidAPI disponibles."""
        keys = []
        if self.rapidapi_key:
            keys.append(self.rapidapi_key)
        for i in range(2, 10):
            key = getattr(self, f"rapidapi_key_{i}", None) or \
                  getattr(self, f"rapidapi_key_{i}", "")
            if key:
                keys.append(key)
        return keys


settings = Settings()
