# Architecture Technique — Hub_Alex (GCP Native Serverless)

Ce document décrit l'architecture globale, les composants techniques et les principes directeurs de la Plateforme d'Automatisation Personnelle **Hub_Alex** déployée sur **Google Cloud Platform (GCP)**.

---

## 1. Philosophie & Principes Directeurs

Le système est conçu selon une architecture **GCP Native Serverless**, éliminant les bases de données lourdes et les outils tiers pour un coût de **0 CHF/mois** (100% couvert par le Free Tier permanent de Google Cloud).

```text
               +───────────────────────────────────────────────────+
               |                    UTILISATEUR                    |
               +───────────────────────────────────────────────────+
                  /                       |                       \
    (Interface Web HTTPS)       (Telegram Mobile)       (Google Cloud Scheduler)
                /                         |                       \
   +────────────────────────+   +────────────────────────+   +────────────────────────+
   | Navigateur Web         |   | Application Telegram   |   | Google Cloud Scheduler |
   | (Google Sign-In 2FA)   |   | (@alex_hub_control_bot)|   | (Lun/Jeu 8h - 7h00)    |
   +────────────────────────+   +────────────────────────+   +────────────────────────+
                \                         |                       /
                 \ (Bearer Token)         | (Webhook Direct HTTPS)| (POST X-API-Key)
                  \                       v                      /
               +───▼────────────────────────────────────────────▼───+
               |           Google Cloud Run : hub_engine            |
               |                                                    |
               |   +────────────────────────────────────────────+   |
               |   |            Agent Coordinateur              |   |
               |   +────────────────────────────────────────────+   |
               |       /              |              |         \    |
               |      v               v              v          v   |
               |  Agent Veille    Agent Veille   Agent Gmail   Agent|
               |      IA           Parapente      (Triage &   Agenda|
               |  (Modèles/Dev)   (FSVL/Matos)   Brouillons)        |
               +───────────────────────┬────────────────────────────+
                                       │
                    +──────────────────┴──────────────────+
                    │                                     │
                    ▼                                     ▼
         +─────────────────────+               +─────────────────────+
         |     Boîte Gmail     |               |    Cloud Logging    |
         | (alex.florentin...) |               | (Journaux Stack)    |
         +─────────────────────+               +─────────────────────+
```

### Principes Clés :
* **Serverless & Zéro Coût** : Hébergement sur Google Cloud Run avec mise à l'échelle automatique jusqu'à 0 instance (0 CHF de coût fixe).
* **Sécurité à 3 Verrous** :
  1. *Verrou 1 (Web)* : Authentification **Google Sign-In (OAuth2 / 2FA)** restreinte à `alex.florentin@gmail.com`.
  2. *Verrou 2 (API)* : En-tête de sécurité `X-API-Key` pour les appels Cloud Scheduler et scripts autorisés.
  3. *Verrou 3 (Telegram)* : Whitelist stricte sur l'identifiant numérique Telegram de l'utilisateur (`ALLOWED_TELEGRAM_USER_ID`).
* **Messagerie & Sécurité des E-mails** :
  * *Vers Alexandre (`alex.florentin@gmail.com`)* : Envoi direct des newsletters HTML et rapports.
  * *Vers des tiers* : Création exclusive de **Brouillons (Drafts)** dans Gmail.
* **Mémoire Git-Native** : La mémoire froide et les préférences sont stockées sous forme de fichiers Markdown dans le dépôt Git (`docs/memory/`).
* **Journaux Cloud** : Tous les logs sont capturés par Google Cloud Logging (Stackdriver) avec recherche et métriques intégrées.

---

## 2. Composants du Système

### 2.1 Le Moteur Backend (`projects/hub_engine`)
* **Framework Web** : FastAPI (Python 3.11).
* **Framework d'Agents** : PydanticAI (type-safe, structuré, cascade de modèles Gemini 3.6/3.7/3.5/Flash-Latest).
* **Service Gmail** (`app/services/gmail_service.py`) : Connexion par Mot de passe d'application (SMTP SSL 465 / IMAP SSL 993) ou OAuth2 API.
* **Service RSS** (`app/services/rss_service.py`) : Moteur asynchrone de collecte et dé-duplication de flux.
* **Service Aérologie & Météo** (`app/services/weather_service.py` & `app/agents/meteo_parapente.py`) : Prévisions Open-Meteo haute résolution pour 4 spots clés (Salève, Jura, Valais, Val d'Illiez), calculs de gradients de pression synoptiques (Bise, Foehn) et arbitrage vol libre.
* **Webhook Telegram Direct Asynchrone** (`app/main.py` & `app/services/telegram_service.py`) :
  * Endpoint `/api/v1/telegram/webhook` avec acquittement immédiat HTTP 200 (< 50ms) délégué aux `BackgroundTasks` pour éliminer tout risque de timeout et de boucle de relance Telegram.
  * Cache LRU de déduplication des `update_id` (15 minutes de TTL) pour filtrer les réémissions résiduelles.
  * Envoi d'un indicateur visuel d'activité `typing` dès la réception de la commande.

### 2.2 Orchestration & Automatisation GCP
* **Google Cloud Scheduler** : Déclencheurs cron sans serveur (0 CHF) configurés pour :
  * *Veille IA Hebdomadaire* : Tous les lundis à 08h00 (`weekly-ai-news` -> Telegram + Email).
  * *Météo Parapente & Perspective Semaine* : Tous les lundis à 14h00 (`meteo-week-outlook` -> Telegram + Email).
  * *Veille Parapente & Matériel* : Tous les jeudis à 08h00 (`weekly-parapente-news` -> Telegram + Email).
  * *Météo Parapente & Anticipation Week-end* : Tous les vendredis à 08h00 (`meteo-weekend-briefing` -> Telegram + Email).
  * *Briefing Quotidien* : Tous les matins à 07h00 (`daily-briefing`).
* **Google Artifact Registry** : Dépôt sécurisé d'images Docker (`hub-alex-repo`).
* **GitHub Actions** : Pipeline CI/CD qui compile et déploie le conteneur automatiquement sur Cloud Run à chaque `git push origin main`.

