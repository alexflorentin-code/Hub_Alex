import os
import re
import imaplib
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("archive_old_emails")

def load_env() -> Dict[str, str]:
    """Charge les variables d'environnement depuis le fichier .env."""
    env = {}
    possible_paths = [
        os.path.abspath(".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
    ]
    for env_path in possible_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"^([A-Za-z0-9_]+)=(.*)$", line.strip())
                    if m:
                        env[m.group(1)] = m.group(2).strip()
            if env.get("ALLOWED_GOOGLE_EMAIL"):
                break
    return env

def chunk_list(lst: list, chunk_size: int = 100):
    """Découpe une liste en sous-listes de taille chunk_size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def archive_old_inbox_emails(before_date_str: str = "2025/01/01"):
    """Archive tous les e-mails de l'INBOX antérieurs à la date spécifiée."""
    env = load_env()
    email_user = env.get("ALLOWED_GOOGLE_EMAIL")
    app_pwd = env.get("GMAIL_APP_PASSWORD", "").replace(" ", "")

    if not email_user or not app_pwd:
        logger.error("Identifiants Gmail manquants dans .env.")
        return

    logger.info(f"Connexion IMAP à Gmail pour {email_user}...")
    with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
        mail.login(email_user, app_pwd)
        mail.select("INBOX")

        query = f"in:inbox before:{before_date_str}"
        logger.info(f"Recherche des e-mails dans INBOX avec la requête : {query}")
        
        status, data = mail.search(None, "X-GM-RAW", f'\"{query}\"')
        if status != "OK" or not data or not data[0]:
            logger.info("Aucun e-mail antérieur trouvé dans l'INBOX.")
            return

        msg_ids = data[0].split()
        count = len(msg_ids)
        logger.info(f"==> {count} e-mails antérieurs au {before_date_str} trouvés dans l'INBOX.")

        processed = 0
        for chunk in chunk_list(msg_ids, chunk_size=100):
            chunk_str = b",".join(chunk).decode("utf-8")
            
            # Marquer pour archivage (retrait du dossier INBOX)
            mail.store(chunk_str, "+FLAGS", r"(\Deleted)")
            processed += len(chunk)
            logger.info(f"  -> Progression archivage : {processed}/{count} e-mails traités")

        logger.info("Validation de l'archivage dans INBOX (expunge)...")
        mail.expunge()

        # État final de l'INBOX
        status, data_all = mail.search(None, "ALL")
        total_remaining = len(data_all[0].split()) if data_all and data_all[0] else 0
        
        status, data_unseen = mail.search(None, "UNSEEN")
        unseen_remaining = len(data_unseen[0].split()) if data_unseen and data_unseen[0] else 0

        logger.info(f"\n==========================================")
        logger.info(f"BILAN DE L'ARCHIVAGE DES ANCIENS E-MAILS :")
        logger.info(f"Messages archivés (< {before_date_str}) : {processed}")
        logger.info(f"Messages restants dans INBOX : {total_remaining} (dont non lus : {unseen_remaining})")
        logger.info(f"==========================================")

if __name__ == "__main__":
    archive_old_inbox_emails(before_date_str="2025/01/01")
