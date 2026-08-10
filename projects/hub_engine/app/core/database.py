from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# Configuration du moteur de base de données SQLite
# connect_args={"check_same_thread": False} est nécessaire uniquement pour SQLite
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dépendance pour injecter la session de base de données dans les routes FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
