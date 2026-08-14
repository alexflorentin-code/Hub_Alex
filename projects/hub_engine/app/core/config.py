import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Port d'écoute (injecté automatiquement par Google Cloud Run via la variable PORT)
    PORT: int = 8000

    # Sécurité & Authentification
    # API_KEY est utilisé à la fois comme mot de passe pour Basic Auth et pour l'en-tête X-API-Key
    API_KEY: str = "alex"
    BASIC_AUTH_USERNAME: str = "alex"
    
    # Clés LLM (Google Gemini par défaut)
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Configuration Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    ALLOWED_TELEGRAM_USER_ID: Optional[int] = None
    
    # Dossier contenant la mémoire et les préférences Markdown
    DOCS_DIR: str = "../../docs"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
