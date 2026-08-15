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

def markdown_to_html_newsletter(markdown_text: str, title: str = "Hub_Alex Newsletter") -> str:
    """Convertit une synthèse Markdown en un e-mail HTML soigné et moderne."""
    import re
    
    html_lines = []
    lines = markdown_text.split("\n")
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_lines.append("<br/>")
            continue
        
        # Titres
        if stripped.startswith("# "):
            h_text = stripped[2:].strip()
            html_lines.append(f"<h1 style='color:#1e293b; font-size:24px; margin-top:24px; margin-bottom:12px; font-weight:800; border-bottom:2px solid #6366f1; padding-bottom:8px;'>{h_text}</h1>")
        elif stripped.startswith("## "):
            h_text = stripped[3:].strip()
            html_lines.append(f"<h2 style='color:#334155; font-size:19px; margin-top:20px; margin-bottom:10px; font-weight:700;'>{h_text}</h2>")
        elif stripped.startswith("### "):
            h_text = stripped[4:].strip()
            html_lines.append(f"<h3 style='color:#475569; font-size:16px; margin-top:16px; margin-bottom:6px; font-weight:600;'>{h_text}</h3>")
        elif stripped.startswith("> "):
            q_text = stripped[2:].strip()
            html_lines.append(f"<blockquote style='background:#f8fafc; border-left:4px solid #6366f1; margin:12px 0; padding:12px 16px; color:#475569; font-style:italic;'>{q_text}</blockquote>")
        elif stripped.startswith("* ") or stripped.startswith("- ") or stripped.startswith("• "):
            li_text = stripped[2:].strip()
            # Transformation des liens [Titre](url)
            li_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r"<a href='\2' style='color:#4f46e5; text-decoration:underline; font-weight:600;' target='_blank'>\1</a>", li_text)
            # Transformation du gras **texte**
            li_text = re.sub(r'\*\*([^*]+)\*\*', r"<strong>\1</strong>", li_text)
            html_lines.append(f"<li style='margin-bottom:8px; line-height:1.6; color:#334155;'>{li_text}</li>")
        else:
            p_text = stripped
            p_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r"<a href='\2' style='color:#4f46e5; text-decoration:underline; font-weight:600;' target='_blank'>\1</a>", p_text)
            p_text = re.sub(r'\*\*([^*]+)\*\*', r"<strong>\1</strong>", p_text)
            html_lines.append(f"<p style='margin-bottom:12px; line-height:1.6; color:#334155;'>{p_text}</p>")
            
    content_body = "\n".join(html_lines)
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin:0; padding:20px; background-color:#f1f5f9; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width:680px; margin:0 auto; background-color:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <!-- En-tête -->
            <div style="background:linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding:28px 32px; color:#ffffff;">
                <span style="background-color:rgba(99, 102, 241, 0.3); color:#c7d2fe; font-size:12px; font-weight:700; padding:4px 10px; border-radius:20px; text-transform:uppercase; letter-spacing:0.05em;">Hub_Alex • Newsletter Hebdomadaire</span>
                <h1 style="margin:12px 0 0 0; font-size:22px; font-weight:800; color:#ffffff;">{title}</h1>
            </div>
            <!-- Contenu -->
            <div style="padding:32px; font-size:15px; color:#334155;">
                {content_body}
            </div>
            <!-- Pied de page -->
            <div style="background-color:#f8fafc; padding:20px 32px; text-align:center; border-top:1px solid #e2e8f0; font-size:12px; color:#94a3b8;">
                <p style="margin:0;">Généré automatiquement par votre moteur personnel <strong>Hub_Alex</strong> (Google Cloud Run).</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template

def send_email_to_self(subject: str, markdown_content: str) -> dict:
    """Envoie une newsletter ou un rapport directement dans la boîte Gmail d'Alexandre."""
    recipient_email = settings.ALLOWED_GOOGLE_EMAIL
    if not recipient_email:
        raise ValueError("Adresse e-mail du propriétaire (ALLOWED_GOOGLE_EMAIL) non définie.")
    
    service = get_gmail_service()
    if not service:
        logger.warning(f"Envoi d'e-mail à soi-même simulé (service Gmail non connecté) vers {recipient_email}.")
        return {
            "status": "simulated",
            "to": recipient_email,
            "subject": subject
        }

    try:
        message = PyEmailMessage()
        message["To"] = recipient_email
        message["From"] = recipient_email
        message["Subject"] = subject
        
        # Version texte brut
        message.set_content(markdown_content)
        
        # Version HTML riche
        html_body = markdown_to_html_newsletter(markdown_content, title=subject)
        message.add_alternative(html_body, subtype="html")

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        sent_msg = service.users().messages().send(
            userId="me",
            body={"raw": encoded_message}
        ).execute()
        
        msg_id = sent_msg.get("id", "unknown")
        logger.info(f"Newsletter envoyée avec succès à {recipient_email} (Message ID: {msg_id}).")
        
        return {
            "status": "sent",
            "message_id": msg_id,
            "to": recipient_email,
            "subject": subject
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'e-mail à soi-même : {str(e)}")
        raise e

