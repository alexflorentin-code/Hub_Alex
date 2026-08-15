import os
import base64
import logging
from typing import List, Optional, Tuple
from email.message import EmailMessage as PyEmailMessage
from pydantic import BaseModel
from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build, Resource

from app.core.config import settings

logger = logging.getLogger("hub_engine.gmail")

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify"
]

class EmailItem(BaseModel):
    id: str
    thread_id: str
    sender: str
    sender_name: str
    subject: str
    date: str
    snippet: str
    body_text: str

class DraftResult(BaseModel):
    status: str
    draft_id: str
    to: str
    subject: str
    body: str

def get_gmail_service() -> Optional[Resource]:
    """Construit et retourne le client Gmail API authentifié avec le Refresh Token."""
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GMAIL_CLIENT_SECRET
    refresh_token = settings.GMAIL_REFRESH_TOKEN

    if not (client_id and client_secret and refresh_token):
        logger.info("Service Gmail non initialisé : identifiants ou Refresh Token manquants.")
        return None

    try:
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=GMAIL_SCOPES
        )
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du service Gmail : {str(e)}")
        return None

def generate_gmail_auth_url(redirect_uri: str) -> str:
    """Génère l'URL de consentement Google OAuth2 pour autoriser l'accès Gmail."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return auth_url

def exchange_auth_code_for_token(code: str, redirect_uri: str) -> str:
    """Échange le code d'autorisation contre un Refresh Token persistant."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GMAIL_SCOPES, redirect_uri=redirect_uri)
    flow.fetch_token(code=code)
    return flow.credentials.refresh_token

def extract_body_from_payload(payload: dict) -> str:
    """Extrait le texte brut d'un payload d'e-mail (multipart ou plain)."""
    body_text = ""
    try:
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                data = part.get("body", {}).get("data", "")
                if mime_type == "text/plain" and data:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    body_text += decoded + "\n"
                elif mime_type == "text/html" and data and not body_text:
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(decoded, "html.parser")
                    body_text += soup.get_text(separator=" ", strip=True) + "\n"
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                body_text = decoded
    except Exception as e:
        logger.warning(f"Erreur d'extraction du corps du mail : {str(e)}")

    return body_text.strip()

def fetch_unread_emails(max_results: int = 10) -> List[EmailItem]:
    """Récupère les e-mails non lus de la boîte de réception."""
    service = get_gmail_service()
    if not service:
        logger.info("Mode démo Gmail ou service non configuré.")
        return []

    emails: List[EmailItem] = []
    try:
        results = service.users().messages().list(
            userId="me",
            q="is:unread in:inbox",
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()

            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])

            subject = ""
            sender = ""
            date_str = ""

            for h in headers:
                name = h.get("name", "").lower()
                if name == "subject":
                    subject = h.get("value", "")
                elif name == "from":
                    sender = h.get("value", "")
                elif name == "date":
                    date_str = h.get("value", "")

            # Extraction du nom d'expéditeur
            sender_name = sender.split("<")[0].replace('"', "").strip() if "<" in sender else sender
            snippet = msg_data.get("snippet", "")
            body = extract_body_from_payload(payload) or snippet

            emails.append(EmailItem(
                id=msg["id"],
                thread_id=msg_data.get("threadId", msg["id"]),
                sender=sender,
                sender_name=sender_name,
                subject=subject or "(Sans sujet)",
                date=date_str,
                snippet=snippet,
                body_text=body
            ))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des e-mails Gmail : {str(e)}")

    return emails

def create_gmail_draft(
    to_email: str,
    subject: str,
    body_text: str,
    thread_id: Optional[str] = None
) -> DraftResult:
    """Crée un brouillon dans la boîte Gmail de l'utilisateur."""
    service = get_gmail_service()
    if not service:
        logger.warning("Création de brouillon simulée (service Gmail non connecté).")
        return DraftResult(
            status="simulated",
            draft_id="simulated-draft-id-123",
            to=to_email,
            subject=subject,
            body=body_text
        )

    try:
        message = PyEmailMessage()
        message.set_content(body_text)
        message["To"] = to_email
        message["Subject"] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_body = {
            "message": {
                "raw": encoded_message
            }
        }
        if thread_id:
            create_body["message"]["threadId"] = thread_id

        draft = service.users().drafts().create(userId="me", body=create_body).execute()
        draft_id = draft.get("id", "unknown")
        logger.info(f"Brouillon Gmail créé avec succès (ID: {draft_id}) pour {to_email}.")

        return DraftResult(
            status="created",
            draft_id=draft_id,
            to=to_email,
            subject=subject,
            body=body_text
        )
    except Exception as e:
        logger.error(f"Erreur lors de la création du brouillon Gmail : {str(e)}")
        raise e
