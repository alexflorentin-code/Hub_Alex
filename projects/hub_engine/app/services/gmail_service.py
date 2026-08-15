import os
import time
import base64
import smtplib
import imaplib
import email
from email.header import decode_header
from email.message import EmailMessage as PyEmailMessage
import logging
from typing import List, Optional, Tuple
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
        logger.error(f"Erreur lors de l'initialisation du service Gmail API : {str(e)}")
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

def decode_mime_header(val: str) -> str:
    """Décode les en-têtes MIME (ex: =?utf-8?B?...?=)."""
    if not val:
        return ""
    decoded_parts = decode_header(val)
    res = ""
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            res += part.decode(enc or "utf-8", errors="ignore")
        else:
            res += str(part)
    return res

def fetch_unread_emails(max_results: int = 10) -> List[EmailItem]:
    """Récupère les e-mails non lus (via App Password / IMAP ou Gmail API)."""
    # 1. Méthode Simple : Mot de Passe d'Application (IMAP SSL)
    if settings.GMAIL_APP_PASSWORD and settings.ALLOWED_GOOGLE_EMAIL:
        emails: List[EmailItem] = []
        try:
            with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
                clean_pw = settings.GMAIL_APP_PASSWORD.replace(" ", "")
                mail.login(settings.ALLOWED_GOOGLE_EMAIL, clean_pw)
                mail.select("INBOX")
                status, data = mail.search(None, "UNSEEN")
                if status == "OK" and data[0]:
                    msg_ids = data[0].split()[-max_results:]
                    for m_id in reversed(msg_ids):
                        _, msg_data = mail.fetch(m_id, "(RFC822)")
                        raw_email = msg_data[0][1]
                        parsed = email.message_from_bytes(raw_email)
                        
                        subject = decode_mime_header(parsed.get("Subject", "(Sans sujet)"))
                        sender = decode_mime_header(parsed.get("From", "Inconnu"))
                        sender_name = sender.split("<")[0].replace('"', '').strip() if "<" in sender else sender
                        date_str = parsed.get("Date", "")
                        
                        body_content = ""
                        if parsed.is_multipart():
                            for part in parsed.walk():
                                c_type = part.get_content_type()
                                if c_type == "text/plain":
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body_content += payload.decode("utf-8", errors="ignore")
                        else:
                            payload = parsed.get_payload(decode=True)
                            if payload:
                                body_content = payload.decode("utf-8", errors="ignore")
                                
                        emails.append(EmailItem(
                            id=m_id.decode(),
                            thread_id=m_id.decode(),
                            sender=sender,
                            sender_name=sender_name,
                            subject=subject,
                            date=date_str,
                            snippet=body_content[:150],
                            body_text=body_content[:600]
                        ))
            return emails
        except Exception as e:
            logger.error(f"Erreur IMAP Gmail : {str(e)}")

    # 2. Méthode OAuth2 : Gmail API
    service = get_gmail_service()
    if service:
        emails = []
        try:
            results = service.users().messages().list(userId="me", q="is:unread in:inbox", maxResults=max_results).execute()
            for msg in results.get("messages", []):
                msg_data = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
                payload = msg_data.get("payload", {})
                headers = payload.get("headers", [])
                subject, sender, date_str = "", "", ""
                for h in headers:
                    n = h.get("name", "").lower()
                    if n == "subject": subject = h.get("value", "")
                    elif n == "from": sender = h.get("value", "")
                    elif n == "date": date_str = h.get("value", "")
                
                sender_name = sender.split("<")[0].replace('"', "").strip() if "<" in sender else sender
                body = extract_body_from_payload(payload) or msg_data.get("snippet", "")
                emails.append(EmailItem(
                    id=msg["id"],
                    thread_id=msg_data.get("threadId", msg["id"]),
                    sender=sender,
                    sender_name=sender_name,
                    subject=subject or "(Sans sujet)",
                    date=date_str,
                    snippet=msg_data.get("snippet", ""),
                    body_text=body
                ))
            return emails
        except Exception as e:
            logger.error(f"Erreur Gmail API : {str(e)}")

    logger.info("Mode démo Gmail ou service non configuré.")
    return []

def find_drafts_mailbox(mail: imaplib.IMAP4_SSL) -> str:
    """Détecte automatiquement le nom exact du dossier Brouillons dans Gmail (FR: [Gmail]/Brouillons, EN: [Gmail]/Drafts)."""
    try:
        typ, data = mail.list()
        if typ == "OK" and data:
            for line in data:
                decoded = line.decode("utf-8", errors="ignore")
                if "\\Drafts" in decoded:
                    parts = decoded.split('"/"')
                    if len(parts) > 1:
                        box_name = parts[1].strip().strip('"')
                        return f'"{box_name}"'
    except Exception as e:
        logger.warning(f"Erreur détection dossier brouillons IMAP : {str(e)}")
    
    return '"[Gmail]/Brouillons"'

def create_gmail_draft(to_email: str, subject: str, body_text: str, thread_id: Optional[str] = None) -> DraftResult:
    """Crée un brouillon dans la boîte Gmail de l'utilisateur."""
    # 1. Méthode Simple : Mot de Passe d'Application (IMAP Append)
    if settings.GMAIL_APP_PASSWORD and settings.ALLOWED_GOOGLE_EMAIL:
        try:
            msg = PyEmailMessage()
            msg.set_content(body_text)
            msg["To"] = to_email
            msg["From"] = settings.ALLOWED_GOOGLE_EMAIL
            msg["Subject"] = subject
            
            clean_pw = settings.GMAIL_APP_PASSWORD.replace(" ", "")
            with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
                mail.login(settings.ALLOWED_GOOGLE_EMAIL, clean_pw)
                draft_folder = find_drafts_mailbox(mail)
                
                res = mail.append(draft_folder, "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                logger.info(f"Brouillon créé via IMAP dans {draft_folder} pour {to_email} (résultat: {res}).")
                
                return DraftResult(
                    status="created",
                    draft_id="imap-draft-id",
                    to=to_email,
                    subject=subject,
                    body=body_text
                )
        except Exception as e:
            logger.error(f"Erreur création brouillon IMAP : {str(e)}")

    # 2. Méthode OAuth2 : Gmail API
    service = get_gmail_service()
    if service:
        try:
            message = PyEmailMessage()
            message.set_content(body_text)
            message["To"] = to_email
            message["Subject"] = subject

            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body_dict = {"message": {"raw": encoded}}
            if thread_id:
                body_dict["message"]["threadId"] = thread_id

            draft = service.users().drafts().create(userId="me", body=body_dict).execute()
            return DraftResult(
                status="created",
                draft_id=draft.get("id", "unknown"),
                to=to_email,
                subject=subject,
                body=body_text
            )
        except Exception as e:
            logger.error(f"Erreur création brouillon API : {str(e)}")
            raise e

    logger.warning("Création de brouillon simulée (service Gmail non connecté).")
    return DraftResult(
        status="simulated",
        draft_id="simulated-draft-id-123",
        to=to_email,
        subject=subject,
        body=body_text
    )

def markdown_to_html_newsletter(markdown_text: str, title: str = "Hub_Alex Newsletter") -> str:
    """Convertit une synthèse Markdown en un e-mail HTML soigné et moderne."""
    import re
    html_lines = []
    for line in markdown_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            html_lines.append("<br/>")
            continue
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
            li_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r"<a href='\2' style='color:#4f46e5; text-decoration:underline; font-weight:600;' target='_blank'>\1</a>", li_text)
            li_text = re.sub(r'\*\*([^*]+)\*\*', r"<strong>\1</strong>", li_text)
            html_lines.append(f"<li style='margin-bottom:8px; line-height:1.6; color:#334155;'>{li_text}</li>")
        else:
            p_text = stripped
            p_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r"<a href='\2' style='color:#4f46e5; text-decoration:underline; font-weight:600;' target='_blank'>\1</a>", p_text)
            p_text = re.sub(r'\*\*([^*]+)\*\*', r"<strong>\1</strong>", p_text)
            html_lines.append(f"<p style='margin-bottom:12px; line-height:1.6; color:#334155;'>{p_text}</p>")
            
    content_body = "\n".join(html_lines)
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body style="margin:0; padding:20px; background-color:#f1f5f9; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width:680px; margin:0 auto; background-color:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <div style="background:linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding:28px 32px; color:#ffffff;">
                <span style="background-color:rgba(99, 102, 241, 0.3); color:#c7d2fe; font-size:12px; font-weight:700; padding:4px 10px; border-radius:20px; text-transform:uppercase; letter-spacing:0.05em;">Hub_Alex • Newsletter Hebdomadaire</span>
                <h1 style="margin:12px 0 0 0; font-size:22px; font-weight:800; color:#ffffff;">{title}</h1>
            </div>
            <div style="padding:32px; font-size:15px; color:#334155;">
                {content_body}
            </div>
            <div style="background-color:#f8fafc; padding:20px 32px; text-align:center; border-top:1px solid #e2e8f0; font-size:12px; color:#94a3b8;">
                <p style="margin:0;">Généré automatiquement par votre moteur personnel <strong>Hub_Alex</strong>.</p>
            </div>
        </div>
    </body>
    </html>
    """

def send_email_to_self(subject: str, markdown_content: str) -> dict:
    """Envoie une newsletter directement dans la boîte Gmail d'Alexandre (SMTP SSL ou Gmail API)."""
    recipient_email = settings.ALLOWED_GOOGLE_EMAIL
    if not recipient_email:
        raise ValueError("Adresse e-mail du propriétaire (ALLOWED_GOOGLE_EMAIL) non définie.")

    message = PyEmailMessage()
    message["To"] = recipient_email
    message["From"] = recipient_email
    message["Subject"] = subject
    message.set_content(markdown_content)
    html_body = markdown_to_html_newsletter(markdown_content, title=subject)
    message.add_alternative(html_body, subtype="html")

    # 1. Méthode Simple : Mot de Passe d'Application (SMTP SSL)
    if settings.GMAIL_APP_PASSWORD:
        try:
            clean_pw = settings.GMAIL_APP_PASSWORD.replace(" ", "")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(recipient_email, clean_pw)
                server.send_message(message)
            logger.info(f"Newsletter envoyée avec succès via SMTP à {recipient_email}.")
            return {"status": "sent", "method": "smtp", "to": recipient_email, "subject": subject}
        except Exception as e:
            logger.error(f"Erreur SMTP Gmail : {str(e)}")

    # 2. Méthode OAuth2 : Gmail API
    service = get_gmail_service()
    if service:
        try:
            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
            sent_msg = service.users().messages().send(userId="me", body={"raw": encoded}).execute()
            return {"status": "sent", "method": "api", "message_id": sent_msg.get("id"), "to": recipient_email, "subject": subject}
        except Exception as e:
            logger.error(f"Erreur API Gmail send : {str(e)}")

    logger.warning(f"Envoi d'e-mail simulé (aucune configuration Gmail active) vers {recipient_email}.")
    return {"status": "simulated", "to": recipient_email, "subject": subject}
