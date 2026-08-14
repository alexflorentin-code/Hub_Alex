import os
import re
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel
import httpx
import feedparser
from bs4 import BeautifulSoup

from app.core.config import settings

logger = logging.getLogger("hub_engine.rss")

class FeedItem(BaseModel):
    title: str
    link: str
    source_name: str
    published: Optional[str] = None
    summary: str

DEFAULT_SOURCES = [
    # Nouveaux Modèles & Frontier Labs
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("Anthropic Engineering", "https://conoro.github.io/anthropic-engineering-rss-feed/anthropic_engineering_rss.xml"),
    # GitHub & Outils
    ("GitHub Trending Python", "https://github-trending-rss.deno.dev/daily?lang=python"),
    ("Simon Willison Weblog", "https://simonwillison.net/atom/entries/"),
    ("Reddit r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/.rss"),
    # Buzz & Débats
    ("Hacker News AI Top", "https://hnrss.org/newest?q=LLM+OR+AI+OR+Claude+OR+GPT&points=50"),
    ("Techmeme", "https://www.techmeme.com/feed.xml"),
    # Business
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
]

def clean_html(raw_html: str, max_chars: int = 350) -> str:
    """Nettoie le code HTML d'un résumé pour en extraire le texte pur."""
    if not raw_html:
        return ""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        # Supprime les espaces multiples et les retours à la ligne superflus
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            return text[:max_chars] + "..."
        return text
    except Exception:
        return raw_html[:max_chars]

async def fetch_single_feed(client: httpx.AsyncClient, source_name: str, url: str) -> List[FeedItem]:
    """Télécharge et parse un flux RSS de manière asynchrone."""
    items: List[FeedItem] = []
    try:
        headers = {
            "User-Agent": "HubAlexBot/1.0 (Personal Tech Watch; +https://github.com/alexflorentin-code/Hub_Alex)"
        }
        resp = await client.get(url, headers=headers, timeout=8.0)
        if resp.status_code != 200:
            logger.warning(f"Impossible de récupérer le flux {source_name} ({url}) : Statut HTTP {resp.status_code}")
            return items

        feed = feedparser.parse(resp.text)
        # Récupérer les 3 articles les plus récents de chaque flux
        for entry in feed.entries[:3]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            published = entry.get("published", entry.get("updated", ""))
            
            raw_summary = entry.get("summary", entry.get("description", ""))
            summary = clean_html(raw_summary)

            if title and link:
                items.append(FeedItem(
                    title=title,
                    link=link,
                    source_name=source_name,
                    published=published,
                    summary=summary
                ))
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture du flux {source_name} ({url}) : {str(e)}")
    
    return items

def load_sources_from_docs() -> List[tuple]:
    """Charge les URLs de flux depuis docs/organization/veille_sources.md si disponible."""
    sources_path = os.path.join(settings.DOCS_DIR, "organization", "veille_sources.md")
    if not os.path.exists(sources_path):
        return DEFAULT_SOURCES

    parsed_sources = []
    try:
        with open(sources_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex pour capturer * **Nom** : `http://...`
        matches = re.findall(r"\*\s+\*\*(.*?)\*\*\s*:\s*`(https?://.*?)`", content)
        for name, url in matches:
            parsed_sources.append((name.strip(), url.strip()))
    except Exception as e:
        logger.error(f"Erreur lors de la lecture de {sources_path} : {str(e)}")

    return parsed_sources if parsed_sources else DEFAULT_SOURCES

async def fetch_all_veille_items() -> List[FeedItem]:
    """Récupère en parallèle les articles de toutes les sources surveillées."""
    sources = load_sources_from_docs()
    logger.info(f"Démarrage de la collecte RSS sur {len(sources)} sources...")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_single_feed(client, name, url) for name, url in sources]
        results = await asyncio.gather(*tasks)

    all_items: List[FeedItem] = []
    seen_links = set()

    for item_list in results:
        for item in item_list:
            if item.link not in seen_links:
                seen_links.add(item.link)
                all_items.append(item)

    logger.info(f"Collecte RSS terminée : {len(all_items)} articles uniques récupérés.")
    return all_items
