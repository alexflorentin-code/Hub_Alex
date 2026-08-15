import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Any

class Settings(BaseSettings):
    # Port d'écoute (injecté automatiquement par Google Cloud Run via la variable PORT)
    PORT: int = 8000

    # Sécurité & Authentification
    API_KEY: str = "alex"
    
    # Authentification Google Sign-In (OAuth2)
    GOOGLE_CLIENT_ID: Optional[str] = None
    ALLOWED_GOOGLE_EMAIL: str = "alex.florentin@gmail.com"
    
    # Intégration Gmail (OAuth2 ou Mot de passe d'application simple)
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_REDIRECT_URI: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None
    
    # Clés LLM (Google Gemini par défaut)
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Configuration Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    ALLOWED_TELEGRAM_USER_ID: Optional[int] = None
    
    # Dossier contenant la mémoire et les préférences Markdown
    DOCS_DIR: str = "../../docs"

    @field_validator("ALLOWED_TELEGRAM_USER_ID", "PORT", mode="before")
    @classmethod
    def parse_optional_int(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        return int(v)

    @field_validator("GOOGLE_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_REDIRECT_URI", "GMAIL_APP_PASSWORD", "GEMINI_API_KEY", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", mode="before")
    @classmethod
    def parse_empty_strings(cls, v: Any) -> Optional[str]:
        if v == "":
            return None
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
