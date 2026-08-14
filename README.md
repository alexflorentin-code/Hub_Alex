# Hub_Alex (Control Center Personnel — GCP Native)

Bienvenue dans votre **Control Center personnel**, une plateforme d'automatisation et d'organisation personnelle 100% Serverless déployée sur **Google Cloud Platform (GCP)** pour **0 CHF / mois** (Free Tier).

---

## 1. Fonctionnement Global

```text
  [ Telegram App ] ------------(Webhook HTTPS Direct)------------> [ Cloud Run : hub_engine ]
                                                                          |
  [ Cloud Scheduler ] --(Requête HTTP 7h00 du matin)--------------------->| (FastAPI + PydanticAI)
                                                                          |
  [ Mémoire & Préférences ] <---(Stockage Git / Markdown)-----------------+
```

### 1.1 L'Orchestration locale (IDE)
* **L'Agent Coordinateur** (`.agents/rules/coordinator.md`) : Chef d'orchestre dans Antigravity pour organiser vos tâches.
* **L'Agent Développeur** (`.agents/rules/developer.md`) : Assistant technique pour coder et faire évoluer le moteur.

### 1.2 L'Orchestration Cloud (GCP)
* **hub_engine (Cloud Run)** : Serveur FastAPI léger hébergeant les agents écrits sous **PydanticAI**.
* **Cloud Scheduler** : Horloge 24/7 gratuite qui déclenche le briefing matinal quotidien à 7h00.
* **Telegram Webhook Direct** : Réception et réponse instantanée aux commandes Telegram sans intermédiaire.
* **Sécurité à 3 Verrous** : Basic Auth native sur le Web (`alex` + mot de passe), en-tête `X-API-Key` sur l'API, et Whitelist de votre ID Telegram unique.

---

## 2. Structure du Dépôt

* `.agents/` : Règles comportementales et guides pour l'agent Antigravity dans l'IDE.
* `.github/workflows/` : Pipeline CI/CD pour déployer automatiquement sur Cloud Run à chaque `git push`.
* `docs/` :
  * `architecture_technique.md` : Architecture globale GCP Native Serverless.
  * `specifications_techniques.md` : Spécifications détaillées des flux et de la sécurité.
  * `process_guides/gcp_and_telegram_setup.md` : Guide pas-à-pas pour configurer GCP et votre Bot Telegram.
  * `memory/` : Préférences et historiques sous format Markdown.
* `projects/hub_engine/` : Code source Python (FastAPI + PydanticAI + Dockerfile).

---

## 3. Guides et Documentation

* 📖 **[Guide de configuration GCP & Telegram](docs/process_guides/gcp_and_telegram_setup.md)**
* 📐 **[Architecture Technique](docs/architecture_technique.md)**
* 🧪 **Lancer les tests en local** :
  ```bash
  docker compose up -d
  docker exec -e PYTHONPATH=/app hub_engine pytest
  ```
