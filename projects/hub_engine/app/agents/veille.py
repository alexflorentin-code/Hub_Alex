import os
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.core.config import settings
from app.services.rss_service import fetch_all_veille_items, FeedItem

logger = logging.getLogger("hub_engine.veille")

class VeilleHighlight(BaseModel):
    category: str = Field(description="Catégorie : Nouveaux Modèles, Outils & GitHub, Sujets Chauds / Débats, ou Business")
    title: str = Field(description="Titre percutant de l'actualité")
    impact_summary: str = Field(description="Explication concise de l'avancée ou de l'intérêt concret pour un développeur/entrepreneur")
    source_name: str = Field(description="Nom du média ou du blog")
    source_link: str = Field(description="Lien URL direct vers la source")

class VeilleDigest(BaseModel):
    status: str = Field(default="success", description="Statut de l'analyse")
    macro_trend: str = Field(description="Analyse synthétique de la grande tendance de fond de la semaine")
    highlights: List[VeilleHighlight] = Field(description="Liste des 4 à 8 pépites les plus marquantes")
    telegram_formatted_message: str = Field(description="Message complet formaté en Markdown pour Telegram avec émojis et liens [Titre](url)")
    email_formatted_digest: str = Field(description="Version longue type Newsletter formatée avec titre, sections et liens pour envoi par e-mail")

GEMINI_CANDIDATE_MODELS = [
    "google:gemini-3.6-flash",
    "google:gemini-3.7-flash",
    "google:gemini-3.5-flash",
    "google:gemini-flash-latest",
    "google:gemini-2.5-flash"
]

SYSTEM_PROMPT = """
Tu es l'Agent de Veille Technologique et IA de Hub_Alex pour Alexandre.
Ton rôle est d'analyser un flux d'actualités brutes issues des meilleurs blogs (OpenAI, DeepMind, Anthropic, Hugging Face, Simon Willison, Reddit LocalLLaMA, GitHub Trending, Hacker News, Techmeme).

Tes objectifs :
1. Prendre de la hauteur et identifier la "Grande Tendance de Fond" de la semaine (ce qui structure le paysage IA en ce moment).
2. Sélectionner les 4 à 8 actualités les plus percutantes en éliminant tout bruit publicitaire.
3. Mettre en valeur :
   - Les Nouveaux Modèles (benchmarks, open-weight vs API).
   - Les Nouveaux Outils & Dépôts GitHub Trending (utilité pratique pour un dev).
   - Les Débats Chauds & Buzz de la communauté.
4. TOUJOURS inclure le lien source cliquable au format Markdown [Nom](url) pour chaque point.
5. Rédiger deux formats de restitution :
   - `telegram_formatted_message` : percutant, concis, aéré avec émojis, parfait pour lecture mobile rapide.
   - `email_formatted_digest` : complet, rédigé avec style sous forme de Newsletter professionnelle.
"""

async def run_veille_analysis(custom_prompt: Optional[str] = None) -> VeilleDigest:
    """Exécute la collecte des flux et l'analyse intelligente avec cascade de secours."""
    logger.info("Lancement de l'analyse de veille...")
    items = await fetch_all_veille_items()

    # Si aucune clé API n'est configurée (mode test unitaire)
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        return VeilleDigest(
            status="success",
            macro_trend="L'essor des modèles de raisonnement et l'accélération des agents légers en local.",
            highlights=[
                VeilleHighlight(
                    category="Nouveaux Modèles",
                    title="Annonce d'un nouveau modèle compact",
                    impact_summary="Performances accrues pour les tâches d'agent et de code.",
                    source_name="OpenAI News",
                    source_link="https://openai.com/news"
                ),
                VeilleHighlight(
                    category="Outils & GitHub",
                    title="Nouveau framework d'agents open-source",
                    impact_summary="Permet d'orchestrer des agents sans latence.",
                    source_name="GitHub Trending",
                    source_link="https://github.com/trending"
                )
            ],
            telegram_formatted_message="📊 *Synthèse Veille IA & Tendances*\n\n🌊 *Tendance :* Modèles compacts & agents.\n\n• [Nouveau Modèle](https://openai.com/news)\n• [Repo GitHub](https://github.com/trending)",
            email_formatted_digest="# Newsletter Veille IA\n\n## Tendance de la semaine\nModèles compacts & agents."
        )

    # Préparation du contexte d'articles pour le LLM
    articles_context = []
    for idx, it in enumerate(items[:25], 1):
        articles_context.append(
            f"[{idx}] Source: {it.source_name}\nTitre: {it.title}\nLien: {it.link}\nRésumé: {it.summary}\n"
        )
    
    context_str = "\n---\n".join(articles_context)
    user_instruction = custom_prompt or "Analyse ces actualités récentes et génère le rapport de veille structuré avec les tendances et les liens sources cliquables."
    full_prompt = f"Voici les articles récents collectés :\n\n{context_str}\n\nConsigne : {user_instruction}"

    # Si OpenAI est configuré
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent = Agent("openai:gpt-4o-mini", output_type=VeilleDigest, system_prompt=SYSTEM_PROMPT)
        result = await agent.run(full_prompt)
        return result.output

    # Cascade multi-modèles Gemini pour résilience 100%
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        last_error = None
        for model_candidate in GEMINI_CANDIDATE_MODELS:
            for attempt in range(2):
                try:
                    logger.info(f"Tentative d'analyse de veille avec {model_candidate} (essai {attempt+1})...")
                    agent = Agent(model_candidate, output_type=VeilleDigest, system_prompt=SYSTEM_PROMPT)
                    result = await agent.run(full_prompt)
                    return result.output
                except Exception as e:
                    last_error = e
                    logger.warning(f"Modèle {model_candidate} indisponible ({str(e)[:100]}). Bascule vers le modèle suivant...")
                    await asyncio.sleep(1.0)
        
        logger.error(f"Tous les modèles Gemini ont échoué : {str(last_error)}")
        raise last_error
