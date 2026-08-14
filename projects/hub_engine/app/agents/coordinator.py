import os
import re
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from .helpers import get_global_agent_context
from app.core.config import settings
from .veille import run_veille_analysis

# Modèle de réponse structurée pour le coordinateur
class CoordinatorResponse(BaseModel):
    status: str = Field(description="Statut de l'exécution: success, warning ou error")
    summary: str = Field(description="Résumé court de la réponse ou de l'action entreprise")
    detailed_response: str = Field(description="Contenu détaillé de la réponse à l'utilisateur (format Markdown)")
    action_taken: str = Field(description="Description de l'action effectuée ou proposée")
    next_steps: list[str] = Field(default=[], description="Liste d'étapes recommandées pour la suite")

# Résolution automatique du modèle LLM
def resolve_model():
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        return "google:gemini-2.5-flash"
    elif settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        return "openai:gpt-4o-mini"
    else:
        # Fallback de test si aucune clé API n'est configurée
        return "test"

# Définition de l'Agent Coordinateur
def get_coordinator_agent() -> Agent:
    model_name = resolve_model()
    
    # Récupérer les contextes et règles locales pour les injecter dans le prompt système
    global_context = get_global_agent_context()
    
    system_prompt = (
        "Tu es l'Agent Coordinateur du Hub personnel d'Alexandre (Hub_Alex).\n"
        "Ton rôle est d'accueillir l'utilisateur, de répondre à ses requêtes et d'orienter les actions.\n\n"
        f"{global_context}\n\n"
        "Directives comportementales :\n"
        "- Sécurité de la messagerie : Ne jamais envoyer de mail direct, uniquement créer des brouillons.\n"
        "- Sécurité du code : Ne jamais modifier ou supprimer de fichier sans consentement.\n"
        "- Style : Sois toujours très synthétique, structuré en Markdown, et utile.\n"
    )
    
    agent = Agent(
        model=model_name,
        output_type=CoordinatorResponse,
        system_prompt=system_prompt
    )
    return agent

async def run_coordinator(user_query: str) -> CoordinatorResponse:
    # 1. Détection des demandes de veille technologique & IA
    veille_keywords = ["veille", "news_ia", "news-ia", "news ia", "actualité", "tendance", "nouveauté", "ia"]
    query_lower = user_query.lower()
    
    # Si la requête porte explicitement sur la veille ou les tendances IA
    if any(k in query_lower for k in ["veille", "news_ia", "news-ia", "tendance ia", "actualités ia", "actualite ia"]):
        veille_digest = await run_veille_analysis(user_query)
        return CoordinatorResponse(
            status="success",
            summary=f"Synthèse Veille IA : {veille_digest.macro_trend[:80]}...",
            detailed_response=veille_digest.telegram_formatted_message,
            action_taken="Collecte RSS et analyse des tendances IA via l'Agent de Veille.",
            next_steps=["Consulter les sources en lien", "Demander un format email / newsletter si souhaité"]
        )

    # 2. Exécution normale du coordinateur
    agent = get_coordinator_agent()
    if resolve_model() == "test":
        return CoordinatorResponse(
            status="success",
            summary="Hub opérationnel en mode test",
            detailed_response="Le moteur du Hub est fonctionnel. Veuillez configurer `GEMINI_API_KEY` ou `OPENAI_API_KEY` dans votre fichier `.env` pour activer les agents IA.",
            action_taken="Exécution d'une réponse simulée.",
            next_steps=["Configurer les clés d'API dans .env", "Lancer docker-compose"]
        )
    
    result = await agent.run(user_query)
    return result.output
