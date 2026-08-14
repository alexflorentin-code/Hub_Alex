import os
import secrets
import logging
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.agents.coordinator import run_coordinator

# Configuration des logs (capturés nativement par Google Cloud Logging)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hub_engine")

app = FastAPI(
    title="Hub_Alex Engine (GCP Native with Google Auth)",
    description="Backend API serverless et agents d'organisation avec Google Sign-In.",
    version="0.3.0"
)

# Modèles Pydantic
class GoogleAuthRequest(BaseModel):
    credential: str

class GoogleAuthResponse(BaseModel):
    status: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-session"

class ChatResponse(BaseModel):
    response: str
    status: str
    summary: str

# 1. Dépendance de Sécurité : Vérification soit par Google ID Token (Web), soit par X-API-Key (CLI / Scheduler)
def verify_access(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    # Méthode 1 : Clé d'API (pour Cloud Scheduler ou appels directs)
    if x_api_key and secrets.compare_digest(x_api_key, settings.API_KEY):
        return {"auth_type": "api_key", "user": "api_user"}

    # Méthode 2 : Jeton Google Sign-In (Bearer Token)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        try:
            # Vérification cryptographique du jeton auprès des serveurs de Google
            id_info = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            email = id_info.get("email")
            email_verified = id_info.get("email_verified", False)
            
            # Vérification de l'adresse email autorisée
            if email_verified and email.lower() == settings.ALLOWED_GOOGLE_EMAIL.lower():
                return {"auth_type": "google", "email": email, "name": id_info.get("name")}
            else:
                logger.warning(f"Accès refusé pour le compte Google non autorisé : {email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Le compte Google {email} n'est pas autorisé à accéder à ce Hub."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur de validation du jeton Google : {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Jeton d'authentification Google invalide ou expiré."
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise : Veuillez vous connecter avec Google ou fournir un en-tête X-API-Key valide."
    )

# --- ENDPOINTS D'AUTHENTIFICATION & CONFIGURATION ---

@app.get("/api/v1/config/auth")
def get_auth_config():
    """Fournit la configuration publique nécessaire au bouton Google Sign-In du frontend."""
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID,
        "allowed_email": settings.ALLOWED_GOOGLE_EMAIL
    }

@app.post("/api/v1/auth/google", response_model=GoogleAuthResponse)
def verify_google_login(request: GoogleAuthRequest):
    """Vérifie le jeton reçu lors du clic sur 'Se connecter avec Google'."""
    try:
        id_info = id_token.verify_oauth2_token(
            request.credential, 
            google_requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        email = id_info.get("email")
        if not id_info.get("email_verified") or email.lower() != settings.ALLOWED_GOOGLE_EMAIL.lower():
            logger.warning(f"Tentative de connexion bloquée pour : {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte Google non autorisé."
            )
            
        return GoogleAuthResponse(
            status="authenticated",
            email=email,
            name=id_info.get("name"),
            picture=id_info.get("picture")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Échec de l'authentification Google : {str(e)}"
        )

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
        "google_auth_configured": settings.GOOGLE_CLIENT_ID is not None,
        "telegram_configured": {
            "token_present": settings.TELEGRAM_BOT_TOKEN is not None,
            "whitelist_active": settings.ALLOWED_TELEGRAM_USER_ID is not None
        }
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user_auth: dict = Depends(verify_access)):
    """Point d'entrée principal pour chatter avec le Coordinateur."""
    logger.info(f"Requête de chat reçue de [{user_auth.get('email') or user_auth.get('user')}] : {request.message[:50]}...")
    agent_response = await run_coordinator(request.message)
    logger.info(f"Réponse de l'agent ({agent_response.status}) : {agent_response.summary}")
    
    return ChatResponse(
        response=agent_response.detailed_response,
        status=agent_response.status,
        summary=agent_response.summary
    )

@app.post("/api/v1/briefing")
async def trigger_briefing(user_auth: dict = Depends(verify_access)):
    """Déclenché tous les matins à 7h par Google Cloud Scheduler."""
    logger.info("Déclenchement du briefing matinal automatique.")
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

    # VERROU DE SÉCURITÉ : Whitelist de l'ID Telegram
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

# --- SERVICE DE L'INTERFACE WEB ---

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    """Sert l'interface Web (la vérification Google Sign-In est gérée côté client et API)."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Interface de chat non disponible."}
