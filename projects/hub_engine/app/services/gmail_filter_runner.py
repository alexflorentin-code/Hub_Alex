import os
import re
import imaplib
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gmail_filter_runner")

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

def run_comprehensive_filters():
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

        rules = [
            {
                "name": "Finance, Crypto & Investissements",
                "label": "6. @Finance &- Investissement",
                "queries": [
                    "swissborg",
                    "october",
                    "viac",
                    "binance",
                    "kraken",
                    "coinbase",
                    "revolut",
                    "crypto",
                    "crowdlending",
                    "yuh",
                    "neon",
                    "bourse",
                    "etoro",
                    "trade republic"
                ],
                "archive": True
            },
            {
                "name": "Emploi & Réseau (Jobup, LinkedIn, etc.)",
                "label": "4. @Emploi &- R&AOk-seau",
                "queries": [
                    "jobup",
                    "linkedin",
                    "indeed",
                    "michaelpage",
                    "hays",
                    "candidat",
                    "recrutement"
                ],
                "archive": True
            },
            {
                "name": "Parapente & Vol Libre (FFVL, FSVL, matos, clubs)",
                "label": "Personnel/Parapente",
                "queries": [
                    "parapente",
                    "ffvl",
                    "fsvl",
                    "ozone",
                    "advance",
                    "niviuk",
                    "flymaster",
                    "xcontest",
                    "vol-libre"
                ],
                "archive": True
            },
            {
                "name": "Hub_Alex (Newsletters & Veilles du Hub)",
                "label": "5. @Hub_Alex",
                "queries": [
                    "Hub_Alex",
                    "HubAlex",
                    "[Hub_Alex]"
                ],
                "archive": False  # Laisse les messages du Hub visibles dans l'INBOX
            },
            {
                "name": "Promotions, Shopping & E-Commerce",
                "label": "2. @Lecture",
                "queries": [
                    "ikea",
                    "promo",
                    "soldes",
                    "remise",
                    "reduction",
                    "newsletter",
                    "frais de port offerts",
                    "moulin du calanquet"
                ],
                "archive": True
            },
            {
                "name": "IncaMail & LVA",
                "label": "Personnel/IncaMail",
                "queries": [
                    "incamail",
                    "lva"
                ],
                "archive": True
            }
        ]

        total_processed = 0

        for rule in rules:
            rule_name = rule["name"]
            target_label = rule["label"]
            archive = rule["archive"]
            
            logger.info(f"\n--- Traitement de la règle : {rule_name} ---")
            all_msg_ids = set()

            for q in rule["queries"]:
                try:
                    status, data = mail.search(None, "X-GM-RAW", f'\"in:inbox {q}\"')
                    if status == "OK" and data and data[0]:
                        ids = data[0].split()
                        all_msg_ids.update(ids)
                        if ids:
                            logger.info(f"  • Requête 'in:inbox {q}' : {len(ids)} e-mails")
                except Exception as e:
                    logger.warning(f"  • Erreur sur la requête '{q}' : {e}")

            msg_ids_list = list(all_msg_ids)
            count = len(msg_ids_list)
            logger.info(f"Total unique à traiter pour '{rule_name}' : {count} e-mails")

            if not msg_ids_list:
                continue

            processed_for_rule = 0
            for chunk in chunk_list(msg_ids_list, chunk_size=100):
                chunk_str = b",".join(chunk).decode("utf-8")
                
                # 1. Ajouter le libellé
                if target_label:
                    mail.store(chunk_str, "+X-GM-LABELS", f'("{target_label}")')
                
                # 2. Archiver si demandé
                if archive:
                    mail.store(chunk_str, "+FLAGS", r"(\Deleted)")
                
                processed_for_rule += len(chunk)
                logger.info(f"  -> Avancement {rule_name} : {processed_for_rule}/{count} traités")

            if archive:
                logger.info(f"  -> Validation de l'archivage dans INBOX (expunge)...")
                mail.expunge()

            total_processed += processed_for_rule

        # État final
        status, data_all = mail.search(None, "ALL")
        total_remaining = len(data_all[0].split()) if data_all and data_all[0] else 0
        
        status, data_unseen = mail.search(None, "UNSEEN")
        unseen_remaining = len(data_unseen[0].split()) if data_unseen and data_unseen[0] else 0

        logger.info(f"\n==========================================")
        logger.info(f"BILAN DU NETTOYAGE COMPLET :")
        logger.info(f"Messages traités et classés : {total_processed}")
        logger.info(f"Messages restants dans INBOX : {total_remaining} (dont non lus : {unseen_remaining})")
        logger.info(f"==========================================")

if __name__ == "__main__":
    run_comprehensive_filters()
