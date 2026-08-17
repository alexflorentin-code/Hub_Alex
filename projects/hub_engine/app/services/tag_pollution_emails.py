import os
import re
import imaplib
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tag_pollution_emails")

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

def tag_pollution():
    env = load_env()
    email_user = env.get("ALLOWED_GOOGLE_EMAIL")
    app_pwd = env.get("GMAIL_APP_PASSWORD", "").replace(" ", "")

    if not email_user or not app_pwd:
        logger.error("Identifiants Gmail manquants dans .env.")
        return

    logger.info(f"Connexion IMAP à Gmail pour {email_user}...")
    with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mail:
        mail.login(email_user, app_pwd)

        target_label = "9. @&AOA- Supprimer"
        try:
            mail.create(f'\"{target_label}\"')
        except Exception:
            pass

        # Exclusions de sécurité strictes (ne jamais marquer les factures, banques, contrats, pièces d'identité, parapente)
        exclusion = "-facture -invoice -recu -commande -incamail -schweizerpass -assurance -contrat -banque -impot -taxe -ffvl -fsvl -parapente -ozone -advance -niviuk -vol-libre -shv"

        pollution_rules = [
            (
                "Réseaux sociaux obsolètes (FB, Twitter, Instagram, Pinterest)",
                f"(from:facebookmail.com OR from:twitter.com OR from:x.com OR from:instagram.com OR from:pinterest.com OR from:quora.com) {exclusion}"
            ),
            (
                "Logs & notifications de plateformes (GitHub, Trello, Slack, Jira)",
                f"(from:notifications@github.com OR from:trello.com OR from:slack.com OR from:jira.com OR from:asana.com) {exclusion}"
            ),
            (
                "Promotions & soldes périmées (< 2025)",
                f"(promo OR soldes OR remise OR newsletter OR shopping) before:2025/01/01 {exclusion}"
            ),
            (
                "Alertes d'emploi obsolètes (< 2025)",
                f"(from:jobup.ch OR from:linkedin.com) before:2025/01/01 {exclusion}"
            ),
            (
                "Notifications noreply marketing anciennes (< 2025)",
                f"(from:noreply OR from:no-reply) before:2025/01/01 {exclusion}"
            )
        ]

        mail.select('\"[Gmail]/Tous les messages\"')
        all_candidate_ids = set()

        for name, query in pollution_rules:
            logger.info(f"Recherche pour : {name}")
            try:
                status, data = mail.search(None, "X-GM-RAW", f'\"{query}\"')
                if status == "OK" and data and data[0]:
                    ids = data[0].split()
                    all_candidate_ids.update(ids)
                    logger.info(f"  -> {len(ids)} e-mails trouvés")
            except Exception as e:
                logger.warning(f"  -> Erreur sur '{name}': {e}")

        total_unique = len(all_candidate_ids)
        logger.info(f"\n==========================================")
        logger.info(f"TOTAL UNIQUE À ÉTIQUETER '9. @À Supprimer' : {total_unique} e-mails")
        logger.info(f"==========================================")

        if not all_candidate_ids:
            logger.info("Aucun e-mail à étiqueter.")
            return

        msg_list = list(all_candidate_ids)
        processed = 0

        # Étape 1 : Appliquer le libellé '9. @À Supprimer'
        for chunk in chunk_list(msg_list, chunk_size=100):
            chunk_str = b",".join(chunk).decode("utf-8")
            mail.store(chunk_str, "+X-GM-LABELS", f'("{target_label}")')
            processed += len(chunk)
            logger.info(f"  -> Étiquetage en cours : {processed}/{total_unique} e-mails étiquetés")

        # Étape 2 : Si certains sont encore dans l'INBOX, les archiver de l'INBOX
        mail.select("INBOX")
        status, data_inbox = mail.search(None, "X-GM-RAW", f'\"label:9-a-supprimer\"')
        inbox_ids = data_inbox[0].split() if data_inbox and data_inbox[0] else []
        if inbox_ids:
            logger.info(f"Archivage de {len(inbox_ids)} messages polluants restants dans l'INBOX...")
            for chunk in chunk_list(inbox_ids, chunk_size=100):
                chunk_str = b",".join(chunk).decode("utf-8")
                mail.store(chunk_str, "+FLAGS", r"(\Deleted)")
            mail.expunge()

        # Récapitulatif
        mail.select(f'\"{target_label}\"')
        status, count_data = mail.search(None, "ALL")
        final_count = len(count_data[0].split()) if count_data and count_data[0] else 0

        logger.info(f"\n==========================================")
        logger.info(f"FIN DE L'OPÉRATION :")
        logger.info(f"Dossier '9. @À Supprimer' contient désormais : {final_count} e-mails.")
        logger.info(f"AUCUN e-mail n'a été supprimé définitivement.")
        logger.info(f"==========================================")

if __name__ == "__main__":
    tag_pollution()
