import logging
from typing import Optional, List
import httpx
from app.core.config import settings

logger = logging.getLogger("hub_engine.telegram")

def split_message(text: str, max_length: int = 4000) -> List[str]:
    """Découpe un texte trop long en segments de moins de 4000 caractères tout en préservant les sauts de ligne."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    lines = text.split("\n")
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # Si une seule ligne dépasse max_length
            if len(line) > max_length:
                for i in range(0, len(line), max_length):
                    chunks.append(line[i:i + max_length])
            else:
                current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

async def send_telegram_message(
    text: str,
    chat_id: Optional[int] = None,
    parse_mode: Optional[str] = "Markdown",
    disable_web_page_preview: bool = True
) -> bool:
    """
    Envoie un message sur Telegram de manière ultra-robuste :
    1. Vérifie la configuration du jeton et du chat_id.
    2. Découpe automatiquement les messages dépassant 4000 caractères.
    3. Tente l'envoi en Markdown, et bascule immédiatement en texte brut si Telegram renvoie une erreur de parsing.
    4. Logue systématiquement le statut et les réponses exactes de Telegram.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    target_chat_id = chat_id or settings.ALLOWED_TELEGRAM_USER_ID

    if not token or not target_chat_id:
        logger.warning(
            f"Envoi Telegram ignoré : Configuration incomplète "
            f"(TELEGRAM_BOT_TOKEN={'DÉFINI' if token else 'MANQUANT'}, "
            f"ALLOWED_TELEGRAM_USER_ID={'DÉFINI' if target_chat_id else 'MANQUANT'})."
        )
        return False

    telegram_url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = split_message(text, max_length=4000)
    all_success = True

    async with httpx.AsyncClient(timeout=15.0) as client:
        for index, chunk in enumerate(chunks):
            payload = {
                "chat_id": target_chat_id,
                "text": chunk,
                "disable_web_page_preview": disable_web_page_preview
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode

            try:
                response = await client.post(telegram_url, json=payload)
                
                # Succès immédiat
                if response.status_code == 200:
                    logger.info(f"Message Telegram (partie {index+1}/{len(chunks)}) envoyé avec succès à {target_chat_id}.")
                    continue

                # Si échec dû au formatage Markdown (ex: Bad Request: can't parse entities)
                logger.warning(
                    f"Échec Telegram avec parse_mode='{parse_mode}' "
                    f"(HTTP {response.status_code} : {response.text}). "
                    f"Tentative de repli immédiat en texte brut..."
                )
                
                payload_fallback = {
                    "chat_id": target_chat_id,
                    "text": chunk,
                    "disable_web_page_preview": disable_web_page_preview
                }
                fallback_response = await client.post(telegram_url, json=payload_fallback)
                
                if fallback_response.status_code == 200:
                    logger.info(f"Message Telegram (partie {index+1}/{len(chunks)}) expédié avec succès en mode texte brut de repli !")
                else:
                    logger.error(
                        f"Échec définitif envoi Telegram à {target_chat_id} "
                        f"(HTTP {fallback_response.status_code} : {fallback_response.text})."
                    )
                    all_success = False

            except Exception as e:
                logger.error(f"Exception réseau lors de l'envoi du message Telegram à {target_chat_id} : {str(e)}")
                all_success = False

    return all_success

async def send_chat_action(chat_id: Optional[int] = None, action: str = "typing") -> bool:
    """Envoie une notification d'activité à Telegram (ex: 'typing') pendant que le Hub génère la réponse."""
    token = settings.TELEGRAM_BOT_TOKEN
    target_chat_id = chat_id or settings.ALLOWED_TELEGRAM_USER_ID

    if not token or not target_chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendChatAction"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json={"chat_id": target_chat_id, "action": action})
            return resp.status_code == 200
    except Exception as e:
        logger.debug(f"Notification chat_action Telegram ignorée : {str(e)}")
        return False

async def get_bot_info() -> dict:
    """Vérifie la validité du Bot Token auprès des serveurs de Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN non configuré."}

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                return {"status": "success", "bot": data.get("result")}
            return {"status": "error", "code": resp.status_code, "response": data}
    except Exception as e:
        return {"status": "exception", "error": str(e)}

