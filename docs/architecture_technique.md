# Architecture Technique — Hub_Alex (GCP Native Serverless)

Ce document décrit l'architecture globale, les composants techniques et les principes directeurs de la Plateforme d'Automatisation Personnelle **Hub_Alex** déployée sur **Google Cloud Platform (GCP)**.

---

## 1. Philosophie & Principes Directeurs

Le système est conçu selon une architecture **GCP Native Serverless**, éliminant les bases de données lourdes et les outils tiers pour un coût de **0 CHF/mois** (100% couvert par le Free Tier permanent de Google Cloud).

```text
               +-----------------------------------+
               |            Utilisateur            |
               +-----------------------------------+
                  /                             \
    (Interface Web HTTPS)               (Chat Telegram Mobile)
                /                                 \
   +-----------------------+              +-----------------------+
   |   Navigateur Web      |              |   Telegram App        |
   | (HTTP Basic Auth)     |              +-----------------------+
   +-----------------------+                          |
               \                                      | (Webhook Direct HTTPS)
                \                                     v
                 \                        +-----------------------+
                  \                       | Google Cloud Scheduler|
                   \                      | (Déclenchement 7h00)  |
                    \                     +-----------------------+
                     \                                |
                      \                               | (Appel HTTP /briefing)
                       v                              v
               +----------------------------------------------+
               |        Google Cloud Run : hub_engine         |
               |                                              |
               |   +--------------------------------------+   |
               |   |          Agent Coordinateur          |   |
               |   +--------------------------------------+   |
               |       /              |              \        |
               |      v               v               v       |
               |  Agent Veille   Agent Agenda   Agent Emails  |
               +----------------------------------------------+
                       |                              |
                       v                              v
               +-----------------+            +-----------------+
               |  Stockage Git   |            |  Cloud Logging  |
               | (Markdown/Docs) |            | (Journaux Stack)|
               +-----------------+            +-----------------+
```

### Principes Clés :
* **Serverless & Zéro Coût** : Hébergement sur Google Cloud Run avec mise à l'échelle automatique jusqu'à 0 instance (0 CHF de coût fixe).
* **Sécurité à 3 Verrous** :
  1. *Verrou 1 (Web)* : Authentification HTTP Basic native (`alex` + `API_KEY`) chiffrée par SSL Google.
  2. *Verrou 2 (API)* : En-tête de sécurité `X-API-Key` pour les appels programmatiques.
  3. *Verrou 3 (Telegram)* : Whitelist stricte sur l'identifiant numérique Telegram de l'utilisateur (`ALLOWED_TELEGRAM_USER_ID`).
* **Mémoire Git-Native** : La mémoire froide et les préférences sont stockées sous forme de fichiers Markdown dans le dépôt Git (`docs/memory/`).
* **Journaux Cloud** : Tous les logs sont capturés par Google Cloud Logging (Stackdriver) avec recherche et métriques intégrées.

---

## 2. Composants du Système

### 2.1 Le Moteur Backend (`projects/hub_engine`)
* **Framework Web** : FastAPI (Python 3.11).
* **Framework d'Agents** : PydanticAI (type-safe, structuré, compatible Gemini 2.5/OpenAI).
* **Webhook Telegram Direct** : Endpoint `/api/v1/telegram/webhook` qui reçoit les messages de Telegram et y répond directement en Markdown via l'API Telegram.
* **Briefing Quotidien** : Endpoint `/api/v1/briefing` appelé automatiquement par Cloud Scheduler chaque matin à 7h.

### 2.2 Orchestration & Automatisation GCP
* **Google Cloud Scheduler** : Déclencheur cron sans serveur (0 CHF) configuré pour appeler le briefing à 7h00.
* **Google Artifact Registry** : Dépôt sécurisé d'images Docker.
* **GitHub Actions** : Pipeline CI/CD qui compile et déploie le conteneur automatiquement à chaque `git push origin main`.
