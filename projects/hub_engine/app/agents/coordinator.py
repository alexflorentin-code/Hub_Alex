import os
import re
import asyncio
import logging
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from .helpers import get_global_agent_context
from app.core.config import settings
from .veille import run_veille_analysis

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
        "Ton rôle est d'accueillir l'utilisateur, de répondre à ses requêtes, d'organiser sa journée et d'orienter les actions.\n\n"
        f"{global_context}\n\n"
        "Directives comportementales :\n"
        "- Sécurité de la messagerie : Ne jamais envoyer de mail direct, uniquement créer des brouillons.\n"
        "- Sécurité du code : Ne jamais modifier ou supprimer de fichier sans consentement.\n"
        "- Style : Sois toujours très synthétique, structuré en Markdown, et utile.\n"
    )

async def run_coordinator(user_query: str) -> CoordinatorResponse:
    # 1. Détection élargie des requêtes de veille technologique & IA
    query_lower = user_query.lower()
    veille_triggers = [
        "veille", "news_ia", "news-ia", "news ia", "actualit", "tendance",
        "nouveaut", "modèle", "modele", "quoi de neuf", "dernières nouvelles", "hacker news"
    ]
    
    if any(k in query_lower for k in veille_triggers):
        logger.info(f"Détection d'une intention de veille dans la requête : '{user_query}' -> Délégation à l'Agent de Veille.")
        veille_digest = await run_veille_analysis(user_query)
        return CoordinatorResponse(
            status="success",
            summary=f"Synthèse Veille IA : {veille_digest.macro_trend[:80]}...",
            detailed_response=veille_digest.telegram_formatted_message,
            action_taken="Collecte RSS et analyse des tendances IA via l'Agent de Veille.",
            next_steps=["Consulter les sources en lien", "Demander un format email / newsletter si souhaité"]
        )

    # 2. Exécution simulée si aucune clé API
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        return CoordinatorResponse(
            status="success",
            summary="Hub opérationnel en mode test",
            detailed_response="Le moteur du Hub est fonctionnel. Veuillez configurer `GEMINI_API_KEY` ou `OPENAI_API_KEY` dans votre fichier `.env` pour activer les agents IA.",
            action_taken="Exécution d'une réponse simulée.",
            next_steps=["Configurer les clés d'API dans .env", "Lancer docker-compose"]
        )

    # 3. Exécution avec OpenAI si configuré
    system_prompt = get_coordinator_system_prompt()
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent = Agent("openai:gpt-4o-mini", output_type=CoordinatorResponse, system_prompt=system_prompt)
        result = await agent.run(user_query)
        return result.output

    # 4. Cascade multi-modèles Gemini pour haute disponibilité
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
