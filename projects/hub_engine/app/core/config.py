import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Sécurité
    API_KEY: str = "super-secret-hub-key-change-me"
    
    # Base de données
    # Le fichier SQLite est stocké dans un volume persistant /data en production
    DATABASE_URL: str = "sqlite:///./hub.db"
    
    # LLM APIs (optionnels selon l'usage)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # Dossier pour la mémoire sémantique
    CHROMA_DB_DIR: str = "./chroma"
    
    # Fichiers de mémoire locale (Markdown)
    DOCS_DIR: str = "../../docs"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
