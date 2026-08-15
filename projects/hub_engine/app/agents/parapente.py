import os
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.core.config import settings
from app.services.rss_service import fetch_all_parapente_items, FeedItem

logger = logging.getLogger("hub_engine.parapente")

class ParapenteHighlight(BaseModel):
    category: str = Field(description="Catégorie : Matériel & Sorties, Sécurité & Aérologie, Fédérations (FSVL / FFVL), Cross & Récits, ou Compétition")
    title: str = Field(description="Titre percutant de l'actualité vol libre")
    impact_summary: str = Field(description="Explication concise de l'intérêt pour un pilote (caractéristiques techniques, sécurité, enseignement, réglementation)")
    source_name: str = Field(description="Nom du média, de la fédération ou du blog")
    source_link: str = Field(description="Lien URL direct vers la source")

class ParapenteDigest(BaseModel):
    status: str = Field(default="success", description="Statut de l'analyse")
    macro_trend: str = Field(description="Synthèse de la dynamique actuelle (nouveautés matos, aérologie/saison, actualités fédérales FSVL/FFVL, sécurité)")
    highlights: List[ParapenteHighlight] = Field(description="Liste des 4 à 8 actualités et pépites marquantes")
    telegram_formatted_message: str = Field(description="Message complet formaté en Markdown pour Telegram avec émojis (🪂, 💨, 🛡️, 🏔️) et liens cliquables [Titre](url)")
    email_formatted_digest: str = Field(description="Version longue type Newsletter vol libre complète avec édito, sections structurées et liens pour envoi par e-mail")

GEMINI_CANDIDATE_MODELS = [
    "google:gemini-3.6-flash",
    "google:gemini-3.7-flash",
    "google:gemini-3.5-flash",
    "google:gemini-flash-latest",
    "google:gemini-2.5-flash"
]

SYSTEM_PROMPT = """
Tu es l'Agent de Veille Parapente & Vol Libre de Hub_Alex pour Alexandre.
Ton rôle est d'analyser le flux d'actualités brutes issues des meilleures sources de vol libre (FSVL / SHV Suisse, FFVL, DHV, Cross Country Magazine, Rock the Outdoor, Flybubble, Ziad Bassil, Paragliding Forum).

Tes objectifs prioritaires :
1. **Fédération Suisse de Vol Libre (FSVL / SHV) & Réglementation** :
   - Surveiller les actualités de la FSVL, les évolutions des espaces aériens alpins (CTR, TMA, zones protégées en Suisse/France), et les décisions fédérales.
2. **Sorties Matériel & Innovations** :
   - Suivre les nouvelles ailes homologuées (EN-A, EN-B, EN-C 2-lignes, EN-D, CCC), les sellettes (cocons légers, hike & fly), les parachutes de secours et instruments (GPS, varios, livetracking).
3. **Sécurité, Aérologie & Retours d'Expérience** :
   - Mettre en exergue les analyses d'incidents, les alertes de sécurité constructeurs/fédérales, les conseils météo alpine et de pilotage actif.
4. **Cross (XC), Météo & Événements** :
   - Sélectionner les beaux récits de vol de distance (XC) et les compétitions majeures (PWCA, Red Bull X-Alps).
5. **Restitution** :
   - `telegram_formatted_message` : percutant, aéré, émojis vol libre (🪂, 💨, 🛡️, 🏔️), liens cliquables Markdown [Nom](url).
   - `email_formatted_digest` : rédigé avec passion et précision sous forme de Newsletter complète (Édito du pilote, Nouveautés Matériel, Sécurité & FSVL, Récits de Cross).
"""

async def run_parapente_analysis(custom_prompt: Optional[str] = None) -> ParapenteDigest:
    """Exécute la collecte des flux parapente et l'analyse intelligente avec cascade de secours."""
    logger.info("Lancement de l'analyse de veille Parapente...")
    items = await fetch_all_parapente_items()

    # Si aucune clé API n'est configurée (mode test unitaire / développement sans clé)
    if not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY:
        return ParapenteDigest(
            status="success",
            macro_trend="Innovations continues sur les voiles 2-lignes en EN-C / EN-B sport et renforcement des consignes de sécurité FSVL pour la saison alpine.",
            highlights=[
                ParapenteHighlight(
                    category="Fédérations (FSVL / FFVL)",
                    title="Actualités FSVL : Gestion des espaces aériens et sécurité alpine",
                    impact_summary="Mise à jour des zones de vol et sensibilisation aux conditions thermiques en montagne.",
                    source_name="FSVL / SHV Suisse",
                    source_link="https://www.shv-fsvl.ch/fr/actualites/"
                ),
                ParapenteHighlight(
                    category="Matériel & Sorties",
                    title="Sortie d'une nouvelle aile EN-C 2-lignes ultralégère",
                    impact_summary="Gain de performance en transition avec un poids plume adapté au marche et vol.",
                    source_name="Rock the Outdoor",
                    source_link="https://rocktheoutdoor.com"
                ),
                ParapenteHighlight(
                    category="Sécurité & Aérologie",
                    title="Bulletin Sécurité DHV & Bonnes pratiques de pliage secours",
                    impact_summary="Rappel essentiel sur le contrôle périodique et l'extraction des parachutes sous facteur de charge.",
                    source_name="DHV Sécurité",
                    source_link="https://www.dhv.de"
                )
            ],
            telegram_formatted_message=(
                "🪂 *Veille Parapente & Vol Libre — Hub_Alex*\n\n"
                "💨 *Tendance :* Voiles 2-lignes légères & sécurité alpine FSVL.\n\n"
                "🇨🇭 [FSVL Actualités & Espaces Aériens](https://www.shv-fsvl.ch/fr/actualites/)\n"
                "🪂 [Nouveauté Matos EN-C](https://rocktheoutdoor.com)\n"
                "🛡️ [Sécurité & Secours DHV](https://www.dhv.de)"
            ),
            email_formatted_digest=(
                "# 🪂 Newsletter Vol Libre & Parapente\n\n"
                "## 🏔️ L'Édito du Ciel\n"
                "La tendance actuelle est marquée par la démocratisation des technologies 2-lignes et l'accent mis sur la sécurité en vol thermique alpin.\n\n"
                "## 🇨🇭 Actualités FSVL & Réglementation\n"
                "- [FSVL Actualités](https://www.shv-fsvl.ch/fr/actualites/) : Consignes et espaces aériens.\n\n"
                "## 🛠️ Sorties Matériel & Tests\n"
                "- [Nouveautés Voiles & Sellettes](https://rocktheoutdoor.com) : Tests en vol et comparatifs.\n\n"
                "## 🛡️ Sécurité & Aérologie\n"
                "- [Bulletins de sécurité](https://www.dhv.de) : Bonnes pratiques et retours d'expérience."
            )
        )

    # Préparation du contexte d'articles pour le LLM
    articles_context = []
    for idx, it in enumerate(items[:25], 1):
        articles_context.append(
            f"[{idx}] Source: {it.source_name}\nTitre: {it.title}\nLien: {it.link}\nRésumé: {it.summary}\n"
        )
    
    context_str = "\n---\n".join(articles_context)
    user_instruction = custom_prompt or "Analyse ces actualités de parapente et génère la newsletter structurée avec un focus sur la FSVL, le matériel et la sécurité."
    full_prompt = f"Voici les articles récents collectés dans le monde du parapente et du vol libre :\n\n{context_str}\n\nConsigne : {user_instruction}"

    # Si OpenAI est configuré
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
        agent = Agent("openai:gpt-4o-mini", output_type=ParapenteDigest, system_prompt=SYSTEM_PROMPT)
        result = await agent.run(full_prompt)
        return result.output

    # Cascade multi-modèles Gemini pour résilience 100%
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        last_error = None
        for model_candidate in GEMINI_CANDIDATE_MODELS:
            for attempt in range(2):
                try:
                    logger.info(f"Tentative d'analyse parapente avec {model_candidate} (essai {attempt+1})...")
                    agent = Agent(model_candidate, output_type=ParapenteDigest, system_prompt=SYSTEM_PROMPT)
                    result = await agent.run(full_prompt)
                    return result.output
                except Exception as e:
                    last_error = e
                    logger.warning(f"Modèle {model_candidate} indisponible ({str(e)[:100]}). Bascule vers le modèle suivant...")
                    await asyncio.sleep(1.0)
        
        logger.error(f"Tous les modèles Gemini ont échoué pour la veille parapente : {str(last_error)}")
        raise last_error
