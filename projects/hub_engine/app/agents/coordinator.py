import os
import re
import asyncio
import logging
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from .helpers import get_global_agent_context
from app.core.config import settings
from .veille import run_veille_analysis
from .parapente import run_parapente_analysis
from .meteo_parapente import run_meteo_analysis
from .email_agent import analyze_inbox, draft_email
from app.services.gmail_service import send_email_to_self

logger = logging.getLogger("hub_engine.coordinator")

# Modèle de réponse structurée pour le coordinateur
class CoordinatorResponse(BaseModel):
    status: str = Field(description="Statut de l'exécution: success, warning ou error")
    summary: str = Field(description="Résumé court de la réponse ou de l'action entreprise")
    detailed_response: str = Field(description="Contenu détaillé de la réponse à l'utilisateur (format Markdown)")
    action_taken: str = Field(description="Description de l'action effectuée ou proposée")
    next_steps: list[str] = Field(default=[], description="Liste d'étapes recommandées pour la suite")

GEMINI_COORDINATOR_MODELS = [
    "google:gemini-3.6-flash",
    "google:gemini-3.7-flash",
    "google:gemini-3.5-flash",
    "google:gemini-flash-latest",
    "google:gemini-2.5-flash"
]

def get_coordinator_system_prompt() -> str:
    global_context = get_global_agent_context()
    return (
        "Tu es l'Agent Coordinateur du Hub personnel d'Alexandre (Hub_Alex).\n"
        "Ton rôle est d'accueillir l'utilisateur, de répondre à ses requêtes, d'organiser sa journée, ses e-mails et sa veille.\n\n"
        f"{global_context}\n\n"
        "Directives comportementales :\n"
        "- Sécurité de la messagerie : Ne JAMAIS envoyer de mail direct à des tiers (uniquement des BROUILLONS). L'envoi direct est réservé aux newsletters vers Alexandre lui-même.\n"
        "- Sécurité du code : Ne jamais modifier ou supprimer de fichier sans consentement.\n"
        "- Style : Sois toujours très synthétique, structuré en Markdown, et utile.\n"
    )

async def run_coordinator(user_query: str) -> CoordinatorResponse:
    query_lower = user_query.lower()

    # 1. Détection des demandes d'envoi de Newsletter / Veille par e-mail vers soi-même
    newsletter_triggers = ["newsletter", "par mail", "par e-mail", "par email", "m'envoyer la veille", "envoie la veille", "envoie-moi la veille"]
    if any(k in query_lower for k in newsletter_triggers):
        is_parapente = any(k in query_lower for k in ["parapente", "vol libre", "fsvl", "shv", "ffvl", "dhv", "sellette", "aile"])
        if is_parapente:
            logger.info("Envoi de la Newsletter Parapente par e-mail demandé par l'utilisateur.")
            digest = await run_parapente_analysis()
            subject = "🦅 Hub_Alex — Veille Hebdomadaire Parapente & Vol Libre"
            send_email_to_self(subject=subject, markdown_content=digest.email_formatted_digest)
            return CoordinatorResponse(
                status="success",
                summary=f"Newsletter Parapente envoyée à {settings.ALLOWED_GOOGLE_EMAIL}",
                detailed_response=(
                    f"✉️ **Newsletter Parapente Envoyée par E-mail !**\n\n"
                    f"📬 **Destinataire :** `{settings.ALLOWED_GOOGLE_EMAIL}`\n"
                    f"📌 **Objet :** *{subject}*\n\n"
                    f"🌊 **Tendance :** {digest.macro_trend}\n\n"
                    f"💡 *La version complète HTML avec tous les liens est disponible dans votre boîte Gmail !*"
                ),
                action_taken="Génération du digest et envoi de la newsletter HTML via l'API Gmail.",
                next_steps=["Consulter la boîte de réception Gmail"]
            )
        else:
            logger.info("Envoi de la Newsletter IA par e-mail demandé par l'utilisateur.")
            digest = await run_veille_analysis()
            subject = "🤖 Hub_Alex — Veille Hebdomadaire IA & Nouveaux Modèles"
            send_email_to_self(subject=subject, markdown_content=digest.email_formatted_digest)
            return CoordinatorResponse(
                status="success",
                summary=f"Newsletter IA envoyée à {settings.ALLOWED_GOOGLE_EMAIL}",
                detailed_response=(
                    f"✉️ **Newsletter IA Envoyée par E-mail !**\n\n"
                    f"📬 **Destinataire :** `{settings.ALLOWED_GOOGLE_EMAIL}`\n"
                    f"📌 **Objet :** *{subject}*\n\n"
                    f"⚡ **Tendance :** {digest.macro_trend}\n\n"
                    f"💡 *La version complète HTML avec tous les liens est disponible dans votre boîte Gmail !*"
                ),
                action_taken="Génération du digest et envoi de la newsletter HTML via l'API Gmail.",
                next_steps=["Consulter la boîte de réception Gmail"]
            )

    # 2. Détection des demandes de rédaction de brouillon d'e-mail pour des tiers
    draft_triggers = [
        "rédige un mail", "redige un mail", "rédiger un mail", "rediger un mail",
        "rédige un e-mail", "redige un e-mail", "rédiger un e-mail", "rediger un e-mail",
        "rédige un email", "redige un email", "rédiger un email", "rediger un email",
        "écris un mail", "ecris un mail", "écrire un mail", "ecrire un mail",
        "écris un e-mail", "ecris un e-mail", "écrire un e-mail", "ecrire un e-mail",
        "écris un email", "ecris un email", "écrire un email", "ecrire un email",
        "écris à", "ecris a", "écrire à", "ecrire a",
        "prépare un mail", "prepare un mail", "préparer un mail", "preparer un mail",
        "prépare un e-mail", "prepare un e-mail", "préparer un e-mail", "preparer un e-mail",
        "prépare un email", "prepare un email", "préparer un email", "preparer un email",
        "crée un mail", "cree un mail", "créer un mail", "creer un mail",
        "crée un e-mail", "cree un e-mail", "créer un e-mail", "creer un e-mail",
        "crée un email", "cree un email", "créer un email", "creer un email",
        "fais un mail", "faire un mail", "fais un e-mail", "faire un e-mail", "fais un email", "faire un email",
        "envoie un mail", "envoyer un mail", "envoie un e-mail", "envoyer un e-mail", "envoie un email", "envoyer un email",
        "brouillon", "draft", "mail pour", "e-mail pour", "email pour"
    ]
    if any(k in query_lower for k in draft_triggers):
        logger.info(f"Détection d'une intention de rédaction d'e-mail : '{user_query}'")
        draft = await draft_email(user_query)
        response_text = (
            f"✉️ **Brouillon Gmail Enregistré avec Succès !**\n\n"
            f"👤 **Pour :** `{draft.to}`\n"
            f"📌 **Objet :** *{draft.subject}*\n\n"
            f"📝 **Message :**\n"
            f"```text\n{draft.body}\n```\n\n"
            f"🛡️ *Le brouillon est déposé dans votre boîte Gmail. Vous pouvez le relire et cliquer sur 'Envoyer' quand vous le souhaitez.*"
        )
        return CoordinatorResponse(
            status="success",
            summary=f"Brouillon Gmail créé pour {draft.to}",
            detailed_response=response_text,
            action_taken="Génération du message et enregistrement du brouillon dans Gmail API.",
            next_steps=["Ouvrir Gmail pour relire et expédier le message"]
        )

    # 2. Détection des demandes de consultation / synthèse d'e-mails
    email_triage_triggers = ["mes mails", "mes e-mails", "mes emails", "boîte de réception", "inbox", "mails non lus", "emails non lus", "mails urgents"]
    if any(k in query_lower for k in email_triage_triggers):
        logger.info(f"Détection d'une demande de consultation d'e-mails : '{user_query}'")
        inbox = await analyze_inbox()
        return CoordinatorResponse(
            status="success",
            summary=f"Synthèse Gmail : {inbox.unread_count} message(s) analysé(s)",
            detailed_response=inbox.telegram_formatted_message,
            action_taken="Analyse et classification intelligente des e-mails via l'Agent Gmail.",
            next_steps=["Demander la rédaction d'une réponse pour l'un des e-mails si besoin"]
        )

    # 3. Détection des demandes d'Aérologie, Météo Parapente & Cross
    meteo_triggers = [
        "météo", "meteo", "volable", "voler", "est-ce qu'on vole", "peut-on voler",
        "cross", "plafond", "foehn", "bise", "aérologie", "aerologie",
        "val d'illiez", "sonchaux", "suchet", "vercorin", "jura ou valais",
        "conditions de vol", "synoptique", "anticyclone", "dépression", "depression"
    ]
    if any(k in query_lower for k in meteo_triggers):
        logger.info(f"Détection d'une intention météo vol libre : '{user_query}' -> Délégation à l'Agent Météo Parapente.")
        meteo_digest = await run_meteo_analysis(user_query)
        return CoordinatorResponse(
            status="success",
            summary=f"Bulletin Météo Vol Libre : {meteo_digest.synoptic.regime_name[:70]}",
            detailed_response=meteo_digest.telegram_formatted_message,
            action_taken="Analyse synoptique, calculs de volabilité et potentiel cross via l'Agent Météo Parapente.",
            next_steps=["Consulter les fiches spots détaillées", "Vérifier le Foehn et la Bise avant de monter au décollage"]
        )

    # 4. Détection des demandes de veille Parapente & Matériel / Actualités
    parapente_triggers = [
        "parapente", "vol libre", "fsvl", "shv", "ffvl", "dhv", "sellette", "cocon",
        "xcmag", "cross country", "thermique", "aile en-", "ziad bassil", "rock the outdoor", "flybubble"
    ]
    if any(k in query_lower for k in parapente_triggers):
        logger.info(f"Détection d'une intention de veille Parapente : '{user_query}' -> Délégation à l'Agent Parapente.")
        parapente_digest = await run_parapente_analysis(user_query)
        return CoordinatorResponse(
            status="success",
            summary=f"Synthèse Parapente : {parapente_digest.macro_trend[:80]}...",
            detailed_response=parapente_digest.telegram_formatted_message,
            action_taken="Collecte RSS et analyse vol libre (FSVL, matos, sécurité) via l'Agent Parapente.",
            next_steps=["Consulter les sources en lien", "Demander la version Newsletter e-mail complète si besoin"]
        )

    # 4. Détection des demandes de veille technologique & IA
    veille_triggers = [
        "veille", "news_ia", "news-ia", "news ia", "actualit", "tendance",
        "nouveaut", "modèle", "modele", "quoi de neuf", "dernières nouvelles", "hacker news"
    ]
    if any(k in query_lower for k in veille_triggers):
        logger.info(f"Détection d'une intention de veille : '{user_query}' -> Délégation à l'Agent de Veille.")
        veille_digest = await run_veille_analysis(user_query)
        return CoordinatorResponse(
            status="success",
            summary=f"Synthèse Veille IA : {veille_digest.macro_trend[:80]}...",
            detailed_response=veille_digest.telegram_formatted_message,
            action_taken="Collecte RSS et analyse des tendances IA via l'Agent de Veille.",
            next_steps=["Consulter les sources en lien"]
        )

    # 4. Exécution simulée si aucune clé API
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        return CoordinatorResponse(
            status="success",
            summary="Hub opérationnel en mode test",
            detailed_response="Le moteur du Hub est fonctionnel. Veuillez configurer `GEMINI_API_KEY` ou `OPENAI_API_KEY` dans votre fichier `.env` pour activer les agents IA.",
            action_taken="Exécution d'une réponse simulée.",
            next_steps=["Configurer les clés d'API dans .env", "Lancer docker-compose"]
        )

    # 5. Exécution avec OpenAI si configuré
    system_prompt = get_coordinator_system_prompt()
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent = Agent("openai:gpt-4o-mini", output_type=CoordinatorResponse, system_prompt=system_prompt)
        result = await agent.run(user_query)
        return result.output

    # 6. Cascade multi-modèles Gemini pour haute disponibilité
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        last_error = None
        for model_candidate in GEMINI_COORDINATOR_MODELS:
            for attempt in range(2):
                try:
                    agent = Agent(model_candidate, output_type=CoordinatorResponse, system_prompt=system_prompt)
                    result = await agent.run(user_query)
                    return result.output
                except Exception as e:
                    last_error = e
                    logger.warning(f"Coordinateur : Modèle {model_candidate} indisponible ({str(e)[:100]}). Essai suivant...")
                    await asyncio.sleep(1.0)
        
        logger.error(f"Tous les modèles Gemini du Coordinateur ont échoué : {str(last_error)}")
        raise last_error
