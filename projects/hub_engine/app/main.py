import os
from fastapi import FastAPI, Depends, Header, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db, Base
from app.models.models import ChatMessage, ExecutionLog
from app.agents.coordinator import run_coordinator

# Création des tables SQLite au démarrage (si elles n'existent pas)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hub_Alex Engine",
    description="Backend API et agents d'organisation pour la Plateforme d'Automatisation Personnelle.",
    version="0.1.0"
)

# Sécurité : Dépendance de clé d'API
def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API invalide."
        )
    return x_api_key

# Modèles Pydantic pour les requêtes API
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-session"

class ChatResponse(BaseModel):
    response: str
    status: str
    summary: str

# Endpoints API

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    db: Session = Depends(get_db),
    _ = Depends(verify_api_key)
):
    """Point d'entrée principal pour chatter avec le Coordinateur."""
    try:
        # 1. Sauvegarder le message de l'utilisateur en base
        user_msg = ChatMessage(
            session_id=request.session_id,
            role="user",
            content=request.message
        )
        db.add(user_msg)
        db.commit()
        
        # 2. Exécuter l'agent Coordinateur
        agent_response = await run_coordinator(request.message)
        
        # 3. Sauvegarder la réponse de l'assistant en base
        assistant_msg = ChatMessage(
            session_id=request.session_id,
            role="assistant",
            content=agent_response.detailed_response
        )
        db.add(assistant_msg)
        
        # 4. Enregistrer un journal d'exécution
        exec_log = ExecutionLog(
            agent_name="coordinator",
            status=agent_response.status,
            summary=agent_response.summary,
            decisions=agent_response.action_taken,
            duration_ms=0, # Optionnel : mesurer le temps réel
            estimated_cost=0.0 # Optionnel : estimer le coût des tokens
        )
        db.add(exec_log)
        db.commit()
        
        return ChatResponse(
            response=agent_response.detailed_response,
            status=agent_response.status,
            summary=agent_response.summary
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors du traitement : {str(e)}"
        )

@app.get("/api/v1/health")
def health_check():
    """Endpoint de diagnostic rapide."""
    db_status = "ok"
    try:
        # Tester un appel simple à la base de données
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        
    return {
        "status": "online",
        "database": db_status,
        "llm_configured": {
            "gemini": settings.GEMINI_API_KEY is not None,
            "openai": settings.OPENAI_API_KEY is not None
        }
    }

# Service des fichiers statiques pour l'interface de chat
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # Monter le dossier static pour servir d'autres assets éventuels
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    """Sert l'interface Web conversationnelle par défaut."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Interface de chat non disponible."}
