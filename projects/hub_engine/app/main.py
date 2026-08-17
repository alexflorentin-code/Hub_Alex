import os
import time
import secrets
import logging
from collections import OrderedDict
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status, Request, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.agents.coordinator import run_coordinator
from app.agents.veille import run_veille_analysis, VeilleDigest
from app.agents.parapente import run_parapente_analysis, ParapenteDigest
from app.agents.meteo_parapente import run_meteo_analysis, MeteoParapenteDigest
from app.agents.email_agent import analyze_inbox, draft_email, InboxDigest, DraftProposal
from app.services.telegram_service import send_telegram_message, send_chat_action, get_bot_info, get_webhook_info, flush_telegram_pending_updates


# Configuration des logs (capturés nativement par Google Cloud Logging)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hub_engine")

app = FastAPI(
    title="Hub_Alex Engine (GCP Native — Veille & Gmail Agent)",
    description="Backend API serverless, agents d'organisation, veille et intégration Gmail.",
    version="0.5.0"
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

class CreateDraftRequest(BaseModel):
    instruction: str
    recipient: Optional[str] = None

# Dépendance de Sécurité : Vérification soit par Google ID Token (Web), soit par X-API-Key (CLI / Scheduler)
def verify_access(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    if x_api_key and secrets.compare_digest(x_api_key, settings.API_KEY):
        return {"auth_type": "api_key", "user": "api_user"}

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        try:
            id_info = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            email = id_info.get("email")
            email_verified = id_info.get("email_verified", False)
            
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

# --- ENDPOINTS AUTHENTIFICATION & CONFIGURATION ---

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

# --- FLUX D'AUTORISATION GMAIL OAUTH2 (1-CLIC) ---

@app.get("/api/v1/auth/gmail/connect")
def connect_gmail(request: Request):
    """Redirige vers l'écran d'autorisation Google pour connecter la boîte Gmail."""
    redirect_uri = settings.GMAIL_REDIRECT_URI or str(request.url_for("gmail_callback"))
    auth_url = generate_gmail_auth_url(redirect_uri)
    return RedirectResponse(auth_url)

@app.get("/api/v1/auth/gmail/callback")
def gmail_callback(code: str, request: Request):
    """Reçoit le code d'autorisation et affiche le Refresh Token obtenu."""
    redirect_uri = settings.GMAIL_REDIRECT_URI or str(request.url_for("gmail_callback"))
    try:
        refresh_token = exchange_auth_code_for_token(code, redirect_uri)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Connexion Gmail Réussie</title></head>
        <body style="font-family:sans-serif; background:#0b0d19; color:white; padding:40px; text-align:center;">
            <div style="max-width:600px; margin:0 auto; background:#161c2d; padding:30px; border-radius:16px; border:1px solid #374151;">
                <h1 style="color:#10b981;">✅ Boîte Gmail Connectée !</h1>
                <p>Votre Hub a désormais l'autorisation de lire vos e-mails et d'enregistrer des brouillons.</p>
                <p style="color:#9ca3af; font-size:14px;">Votre Refresh Token persistant :</p>
                <div style="background:#0b0d19; padding:12px; border-radius:8px; word-break:break-all; font-family:monospace; color:#6366f1;">
                    {refresh_token}
                </div>
                <p style="margin-top:20px; font-size:13px; color:#9ca3af;">Copiez ce token dans votre secret GitHub <code>GMAIL_REFRESH_TOKEN</code> pour finaliser l'automatisation 24h/24.</p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        return HTMLResponse(f"<h1>❌ Erreur d'autorisation : {str(e)}</h1>", status_code=400)

# --- ENDPOINTS GMAIL & EMAILS ---

@app.get("/api/v1/emails/unread", response_model=InboxDigest)
async def get_unread_emails_endpoint(user_auth: dict = Depends(verify_access)):
    """Analyse et classifie les e-mails non lus de la boîte de réception."""
    return await analyze_inbox()

@app.post("/api/v1/emails/draft", response_model=DraftProposal)
async def create_draft_endpoint(request: CreateDraftRequest, user_auth: dict = Depends(verify_access)):
    """Génère et enregistre un brouillon dans Gmail selon la consigne donnée."""
    return await draft_email(request.instruction, request.recipient)

@app.post("/api/v1/emails/check-alerts")
async def check_email_alerts_endpoint(user_auth: dict = Depends(verify_access)):
    """Vérifie la boîte de réception et envoie une alerte Telegram si un e-mail urgent est détecté."""
    inbox = await analyze_inbox()
    if inbox.urgent_count > 0 and settings.TELEGRAM_BOT_TOKEN and settings.ALLOWED_TELEGRAM_USER_ID:
        for urgent_mail in inbox.urgent_alerts:
            alert_text = (
                f"🚨 **ALERTE E-MAIL URGENT** 🚨\n\n"
                f"👤 **De :** {urgent_mail.sender}\n"
                f"📌 **Objet :** *{urgent_mail.subject}*\n\n"
                f"📝 **Résumé :** {urgent_mail.summary}\n"
                f"⚡ **Action Requise :** {urgent_mail.action_needed}\n"
            )
            await send_telegram_message(alert_text)
    return {"status": "checked", "urgent_count": inbox.urgent_count}

# --- ENDPOINTS CHAT, VEILLE, MÉTÉO & BRIEFING ---

@app.get("/api/v1/health")
def health_check():
    """Endpoint de diagnostic rapide."""
    return {
        "status": "online",
        "llm_configured": {
            "gemini": settings.GEMINI_API_KEY is not None,
            "openai": settings.OPENAI_API_KEY is not None
        },
        "google_auth_configured": settings.GOOGLE_CLIENT_ID is not None,
        "gmail_configured": (settings.GMAIL_REFRESH_TOKEN is not None) or (settings.GMAIL_APP_PASSWORD is not None),
        "telegram_configured": {
            "token_present": settings.TELEGRAM_BOT_TOKEN is not None,
            "whitelist_active": settings.ALLOWED_TELEGRAM_USER_ID is not None
        }
    }

@app.get("/api/v1/telegram/status")
async def telegram_status(user_auth: dict = Depends(verify_access)):
    """Vérifie l'état de la connexion avec les serveurs de Telegram."""
    bot_info = await get_bot_info()
    webhook_info = await get_webhook_info()
    return {
        "bot_configured": settings.TELEGRAM_BOT_TOKEN is not None,
        "whitelist_user_id": settings.ALLOWED_TELEGRAM_USER_ID,
        "telegram_api_response": bot_info,
        "webhook_info": webhook_info
    }

@app.get("/api/v1/telegram/webhook-info")
async def telegram_webhook_info(user_auth: dict = Depends(verify_access)):
    """Affiche les détails du webhook Telegram et les messages en attente de livraison."""
    return await get_webhook_info()

@app.post("/api/v1/telegram/flush")
async def telegram_flush_updates(user_auth: dict = Depends(verify_access)):
    """Purge immédiatement tous les messages et retries en attente dans la file Telegram."""
    logger.info("Purge manuelle de la file d'attente Telegram demandée...")
    result = await flush_telegram_pending_updates()
    return {
        "status": "flushed",
        "result": result
    }

@app.post("/api/v1/telegram/test")
async def telegram_test_ping(
    message: str = Query("🏓 **Test de connexion Hub_Alex !** Votre bot Telegram fonctionne parfaitement.", description="Message de test"),
    user_auth: dict = Depends(verify_access)
):
    """Envoie un message de test immédiat vers le chat Telegram autorisé."""
    logger.info("Envoi d'un message test sur Telegram...")
    sent = await send_telegram_message(message)
    return {
        "success": sent,
        "chat_id": settings.ALLOWED_TELEGRAM_USER_ID,
        "message": message
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user_auth: dict = Depends(verify_access)):
    """Point d'entrée principal pour chatter avec le Coordinateur."""
    logger.info(f"Requête de chat reçue de [{user_auth.get('email') or user_auth.get('user')}] : {request.message[:50]}...")
    agent_response = await run_coordinator(request.message)
    
    return ChatResponse(
        response=agent_response.detailed_response,
        status=agent_response.status,
        summary=agent_response.summary
    )

@app.post("/api/v1/veille/run", response_model=VeilleDigest)
async def trigger_veille(
    send_telegram: bool = Query(True, description="Envoyer la synthèse sur Telegram si activé"),
    send_email: bool = Query(True, description="Envoyer la version newsletter HTML par e-mail à soi-même"),
    user_auth: dict = Depends(verify_access)
):
    """Exécute l'analyse de veille complète (RSS + PydanticAI)."""
    digest = await run_veille_analysis()

    # 1. Envoi Telegram sécurisé et résilient
    if send_telegram:
        await send_telegram_message(digest.telegram_formatted_message)

    # 2. Envoi E-mail HTML à soi-même
    if send_email and settings.ALLOWED_GOOGLE_EMAIL:
        try:
            from app.services.gmail_service import send_email_to_self
            send_email_to_self(
                subject="🤖 Hub_Alex — Veille Hebdomadaire IA & Nouveaux Modèles",
                markdown_content=digest.email_formatted_digest
            )
        except Exception as e:
            logger.warning(f"Impossible d'envoyer la newsletter IA par e-mail : {str(e)}")

    return digest

@app.post("/api/v1/parapente/run", response_model=ParapenteDigest)
async def trigger_parapente(
    send_telegram: bool = Query(True, description="Envoyer la synthèse sur Telegram si activé"),
    send_email: bool = Query(True, description="Envoyer la version newsletter HTML par e-mail à soi-même"),
    user_auth: dict = Depends(verify_access)
):
    """Exécute l'analyse de veille Parapente & Vol Libre (FSVL, matos, sécurité)."""
    logger.info("Exécution de l'Agent Parapente via l'API...")
    digest = await run_parapente_analysis()

    # 1. Envoi Telegram sécurisé et résilient
    if send_telegram:
        await send_telegram_message(digest.telegram_formatted_message)

    # 2. Envoi E-mail HTML à soi-même
    if send_email and settings.ALLOWED_GOOGLE_EMAIL:
        try:
            from app.services.gmail_service import send_email_to_self
            send_email_to_self(
                subject="🦅 Hub_Alex — Veille Hebdomadaire Parapente & Vol Libre",
                markdown_content=digest.email_formatted_digest
            )
        except Exception as e:
            logger.warning(f"Impossible d'envoyer la newsletter Parapente par e-mail : {str(e)}")

    return digest

@app.post("/api/v1/meteo/run", response_model=MeteoParapenteDigest)
async def trigger_meteo(
    send_telegram: bool = Query(True, description="Envoyer le bulletin sur Telegram si activé"),
    send_email: bool = Query(True, description="Envoyer la newsletter météo par e-mail"),
    user_auth: dict = Depends(verify_access)
):
    """Exécute l'analyse d'aérologie, volabilité et potentiel cross pour les Alpes romandes et le Jura."""
    logger.info("Exécution de l'Agent Météo Parapente via l'API...")
    digest = await run_meteo_analysis()

    # 1. Envoi Telegram sécurisé et résilient
    if send_telegram:
        await send_telegram_message(digest.telegram_formatted_message)

    # 2. Envoi E-mail à soi-même
    if send_email and settings.ALLOWED_GOOGLE_EMAIL:
        try:
            from app.services.gmail_service import send_email_to_self
            send_email_to_self(
                subject="🪂 Hub_Alex — Bulletin Météo Parapente & Potentiel Cross",
                markdown_content=digest.email_formatted_digest
            )
        except Exception as e:
            logger.warning(f"Impossible d'envoyer le bulletin météo par e-mail : {str(e)}")

    return digest

@app.post("/api/v1/briefing")
async def trigger_briefing(user_auth: dict = Depends(verify_access)):
    """Déclenché tous les matins à 7h par Google Cloud Scheduler."""
    prompt = "Génère mon briefing matinal complet pour aujourd'hui : priorité des tâches, e-mails importants et agenda."
    agent_response = await run_coordinator(prompt)
    
    await send_telegram_message(f"🌅 *Briefing Quotidien Hub_Alex*\n\n{agent_response.detailed_response}")

    return {
        "status": "success",
        "summary": agent_response.summary,
        "briefing": agent_response.detailed_response
    }

# Cache de déduplication des update_id Telegram (évite les doublons et les boucles de retentative de Telegram)
_processed_telegram_updates: OrderedDict[int, float] = OrderedDict()
MAX_PROCESSED_UPDATES = 1000
UPDATE_EXPIRATION_SECONDS = 900.0  # 15 minutes


def _is_update_already_processed(update_id: int) -> bool:
    """Vérifie si cet update_id a déjà été traité récemment et nettoie le cache expiré."""
    now = time.time()
    # Nettoyage des updates expirés
    while _processed_telegram_updates:
        oldest_id, oldest_time = next(iter(_processed_telegram_updates.items()))
        if now - oldest_time > UPDATE_EXPIRATION_SECONDS or len(_processed_telegram_updates) > MAX_PROCESSED_UPDATES:
            _processed_telegram_updates.pop(oldest_id)
        else:
            break

    if update_id in _processed_telegram_updates:
        return True

    _processed_telegram_updates[update_id] = now
    return False


async def process_telegram_message(chat_id: Optional[int], text: str, sender_id: Optional[int]):
    """
    Traite le message Telegram en tâche de fond (asynchrone).
    Permet à l'API de répondre immédiatement un HTTP 200 OK à Telegram, évitant
    tout timeout et toute réexpédition en boucle (ex: toutes les 2 min).
    """
    if not text:
        return

    logger.info(f"Traitement asynchrone du message Telegram de {sender_id} : {text}")

    # Indiquer immédiatement à Telegram que le bot est en train d'écrire / réfléchir
    if chat_id:
        await send_chat_action(chat_id=chat_id, action="typing")

    reply_text = ""
    try:
        # GESTION DES COMMANDES TELEGRAM
        if text == "/start":
            reply_text = (
                "👋 **Bonjour Alexandre !** Je suis ton Coordinateur Hub_Alex.\n\n"
                "Commandes disponibles :\n"
                "• `/meteo` ou `/cross` : Bulletin Météo Parapente, Volabilité & Arbitrage Jura vs Valais.\n"
                "• `/news_parapente` ou `/parapente` : Veille Vol Libre (FSVL, sorties matériel, sécurité).\n"
                "• `/news_ia` : Lancer la veille IA & top GitHub.\n"
                "• `/emails` ou `/inbox` : Voir la synthèse de ta boîte Gmail.\n"
                "• `/draft <consigne>` : Rédiger un brouillon dans Gmail.\n"
                "• `/briefing` : Recevoir ton briefing du jour.\n"
                "• Ou pose-moi n'importe quelle question en français !"
            )
        elif text.lower() in ["/meteo", "/cross", "/weekend", "/foehn", "/synop", "/voler"]:
            meteo_digest = await run_meteo_analysis()
            reply_text = meteo_digest.telegram_formatted_message
        elif text.lower() in ["/news_ia", "/news-ia", "/newsia", "/veille"]:
            veille_digest = await run_veille_analysis()
            reply_text = veille_digest.telegram_formatted_message
        elif text.lower() in ["/news_parapente", "/news-parapente", "/newsparapente", "/parapente", "/fsvl", "/shv", "/vol_libre", "/vollibre"]:
            parapente_digest = await run_parapente_analysis()
            reply_text = parapente_digest.telegram_formatted_message
        elif text.lower() in ["/emails", "/inbox", "/mails"]:
            inbox_digest = await analyze_inbox()
            reply_text = inbox_digest.telegram_formatted_message
        elif text.lower().startswith("/draft"):
            instruction = text[6:].strip()
            if not instruction:
                reply_text = "ℹ️ Utilisation : `/draft Rédige une réponse à Dupont pour lui dire que je valide le devis`"
            else:
                draft = await draft_email(instruction)
                reply_text = (
                    f"✉️ **Brouillon Gmail Enregistré !**\n\n"
                    f"👤 **Pour :** `{draft.to}`\n"
                    f"📌 **Objet :** *{draft.subject}*\n\n"
                    f"```text\n{draft.body}\n```\n\n"
                    f"🛡️ *Le message est prêt dans votre boîte Gmail.*"
                )
        elif text == "/briefing":
            agent_response = await run_coordinator("Génère mon briefing matinal complet.")
            reply_text = f"🌅 *Briefing Hub_Alex*\n\n{agent_response.detailed_response}"
        else:
            agent_response = await run_coordinator(text)
            reply_text = agent_response.detailed_response

    except Exception as e:
        logger.error(f"Erreur lors du traitement du message Telegram '{text}' : {str(e)}", exc_info=True)
        reply_text = f"⚠️ Une erreur est survenue lors de l'exécution de votre demande : `{str(e)}`"

    # Renvoyer la réponse à l'utilisateur sur Telegram
    if chat_id and reply_text:
        await send_telegram_message(reply_text, chat_id=chat_id)


@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook direct pour recevoir et répondre aux messages Telegram.
    Répond HTTP 200 OK immédiatement (<50ms) et délègue le traitement aux BackgroundTasks,
    ce qui empêche tout timeout côté Telegram et supprime les boucles d'envoi répétées.
    """
    try:
        update = await request.json()
    except Exception:
        return JSONResponse({"status": "invalid json"}, status_code=400)

    # Déduplication par update_id pour bloquer les retries concurrentes ou résiduelles de Telegram
    update_id = update.get("update_id")
    if update_id is not None and _is_update_already_processed(update_id):
        logger.info(f"Update Telegram {update_id} déjà traité (doublon ou retry ignoré).")
        return {"status": "already_processed"}

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"status": "ignored"}

    sender = message.get("from", {})
    sender_id = sender.get("id")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    # Sécurité : Whitelist ID Telegram
    if settings.ALLOWED_TELEGRAM_USER_ID is not None and sender_id != settings.ALLOWED_TELEGRAM_USER_ID:
        logger.warning(f"Accès non autorisé par l'ID Telegram : {sender_id}")
        return {"status": "unauthorized"}

    if not text:
        return {"status": "no text"}

    logger.info(f"Message Telegram reçu de {sender_id} (update_id={update_id}) : {text}")

    # Exécution asynchrone en arrière-plan
    background_tasks.add_task(process_telegram_message, chat_id=chat_id, text=text, sender_id=sender_id)

    return {"status": "ok"}

# --- SERVICE DE L'INTERFACE WEB ---

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    """Sert l'interface Web."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Interface de chat non disponible."}
