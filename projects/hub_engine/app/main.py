import os
import secrets
import logging
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx

from app.core.config import settings
from app.agents.coordinator import run_coordinator

# Configuration des logs (capturés nativement par Google Cloud Logging)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hub_engine")

app = FastAPI(
    title="Hub_Alex Engine (GCP Native)",
    description="Backend API serverless et agents d'organisation pour Hub_Alex.",
    version="0.2.0"
)

security = HTTPBasic()

# 1. Sécurité : HTTP Basic Auth pour l'interface Web
def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.BASIC_AUTH_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.API_KEY)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# 2. Sécurité : Vérification de la clé d'API pour les appels programmatiques
def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if not secrets.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API invalide."
        )
    return x_api_key

# Modèles Pydantic pour les requêtes
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-session"

class ChatResponse(BaseModel):
    response: str
    status: str
    summary: str

# --- ENDPOINTS API ---

@app.get("/api/v1/health")
def health_check():
    """Endpoint de diagnostic rapide pour Cloud Run et Cloud Monitoring."""
    return {
        "status": "online",
        "llm_configured": {
            "gemini": settings.GEMINI_API_KEY is not None,
            "openai": settings.OPENAI_API_KEY is not None
        },
        "telegram_configured": {
            "token_present": settings.TELEGRAM_BOT_TOKEN is not None,
            "whitelist_active": settings.ALLOWED_TELEGRAM_USER_ID is not None
        }
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, _ = Depends(verify_api_key)):
    """Point d'entrée principal pour chatter avec le Coordinateur."""
    logger.info(f"Requête de chat reçue : {request.message[:50]}...")
    agent_response = await run_coordinator(request.message)
    logger.info(f"Réponse de l'agent ({agent_response.status}) : {agent_response.summary}")
    
    return ChatResponse(
        response=agent_response.detailed_response,
        status=agent_response.status,
        summary=agent_response.summary
    )

@app.post("/api/v1/briefing")
async def trigger_briefing(_ = Depends(verify_api_key)):
    """Déclenché tous les matins à 7h par Google Cloud Scheduler."""
    logger.info("Déclenchement du briefing matinal automatique par Cloud Scheduler.")
    prompt = "Génère mon briefing matinal complet pour aujourd'hui : priorité des tâches, veille et agenda."
    agent_response = await run_coordinator(prompt)
    
    # Si Telegram est configuré, envoyer directement le briefing sur le téléphone
    if settings.TELEGRAM_BOT_TOKEN and settings.ALLOWED_TELEGRAM_USER_ID:
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.ALLOWED_TELEGRAM_USER_ID,
            "text": f"🌅 *Briefing Quotidien Hub_Alex*\n\n{agent_response.detailed_response}",
            "parse_mode": "Markdown"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(telegram_url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Erreur d'envoi Telegram : {resp.text}")
            else:
                logger.info("Briefing envoyé sur Telegram avec succès.")

    return {
        "status": "success",
        "summary": agent_response.summary,
        "briefing": agent_response.detailed_response
    }

@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(request: Request):
    """Webhook direct pour recevoir et répondre aux messages Telegram."""
    try:
        update = await request.json()
    except Exception:
        return JSONResponse({"status": "invalid json"}, status_code=400)

    # Récupérer le message et l'expéditeur
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"status": "ignored"}

    sender = message.get("from", {})
    sender_id = sender.get("id")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    # VERROU DE SÉCURITÉ 3 : Whitelist de l'ID Telegram
    if settings.ALLOWED_TELEGRAM_USER_ID is not None and sender_id != settings.ALLOWED_TELEGRAM_USER_ID:
        logger.warning(f"Tentative d'accès non autorisée par l'ID Telegram : {sender_id} (Nom: {sender.get('first_name')})")
        return {"status": "unauthorized"}

    if not text:
        return {"status": "no text"}

    logger.info(f"Message Telegram reçu de l'utilisateur {sender_id} : {text}")

    # Gérer les commandes de base
    if text == "/start":
        reply_text = "👋 Bonjour Alexandre ! Je suis ton Coordinateur Hub_Alex sur Cloud Run. Que puis-je faire pour toi ?"
    else:
        # Exécuter l'Agent Coordinateur
        agent_response = await run_coordinator(text)
        reply_text = agent_response.detailed_response

    # Renvoyer la réponse à l'utilisateur sur Telegram
    if settings.TELEGRAM_BOT_TOKEN and chat_id:
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": reply_text,
            "parse_mode": "Markdown"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(telegram_url, json=payload)
                if resp.status_code != 200:
                    # Si le parsing Markdown échoue (caractères spéciaux), renvoyer en texte brut
                    payload.pop("parse_mode")
                    await client.post(telegram_url, json=payload)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de la réponse Telegram : {str(e)}")

    return {"status": "ok"}

# --- SERVICE DE L'INTERFACE WEB SÉCURISÉE (VERROU 1) ---

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index(_: str = Depends(verify_basic_auth)):
    """Sert l'interface Web, protégée par HTTP Basic Auth."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Interface de chat non disponible."}
