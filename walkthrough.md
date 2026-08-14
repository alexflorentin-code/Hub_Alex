# Walkthrough — Phase 1 : Agent de Veille Technologique & IA

L'**Agent de Veille IA** (Phase 1) est désormais entièrement développé, validé par **14 tests unitaires (100% de réussite)** et déployé sur **Google Cloud Run** via GitHub Actions.

---

## 🌟 Ce qui a été développé

### 1. Sourcing & Flux Curatés ([veille_sources.md](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/organization/veille_sources.md))
Surveillance automatique des 4 piliers d'excellence IA :
* **Nouveaux Modèles & Frontier Labs** : OpenAI News, Google DeepMind / AI Blog, Hugging Face Blog, Anthropic Engineering.
* **Top Dépôts GitHub & Outils Développeur** : GitHub Trending Python/IA, Simon Willison Weblog, Reddit r/LocalLLaMA.
* **Débats & Buzz Communautaire** : Hacker News (Score > 50 pts), Techmeme.
* **Business & Startups** : VentureBeat AI.

### 2. Moteur Asynchrone & Parsing RSS ([rss_service.py](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/projects/hub_engine/app/services/rss_service.py))
* Téléchargement parallèle haute performance via `httpx.AsyncClient`.
* Nettoyage du HTML des articles avec `BeautifulSoup`.
* Dé-duplication automatique des liens et limitation aux articles les plus frais.

### 3. Agent PydanticAI & Double Restitution ([veille.py](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/projects/hub_engine/app/agents/veille.py))
* **Analyse de la Grande Tendance de Fond Hebdomadaire** : Prise de recul sur les mouvements macro.
* **Format Mobile Telegram** (`telegram_formatted_message`) : Condensé percutant avec émojis et liens sources cliquables `[Nom](url)`.
* **Format Email Newsletter** (`email_formatted_digest`) : Digest complet structuré prêt à être envoyé par e-mail ou archivé.

### 4. Commandes Telegram & API ([main.py](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/projects/hub_engine/app/main.py))
* Commande **`/news_ia`** (ou `/news-ia`) disponible directement dans votre chat Telegram.
* Endpoint `POST /api/v1/veille/run` pour déclenchement programmatique ou via Cloud Scheduler.
* Le Coordinateur répond aussi aux requêtes naturelles du type *« Fais-moi le point sur les actualités IA »*.

---

## 🧪 Validation des Tests (14/14 Passed)

```text
tests/test_main.py .........                                             [ 64%]
tests/test_veille.py .....                                               [100%]
======================= 14 passed in 7.11s ========================
```
