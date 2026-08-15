# Hub_Alex — Control Center Personnel (GCP Native & Multi-Agents)

Bienvenue dans votre **Control Center personnel**, une plateforme d'organisation, d'intelligence et d'automatisation 100% Serverless hébergée sur **Google Cloud Platform (GCP)** pour **0 CHF / mois** (Free Tier).

---

## 🌟 Vue d'Ensemble des Fonctionnalités

```text
               +───────────────────────────────────────────────────+
               |                  INTERFACES CLIENT                |
               |                                                   |
               |  📱 Telegram Bot (@alex_hub_control_bot)          |
               |  🌐 Web Interface (Google Sign-In 2FA)            |
               |  ⏰ Google Cloud Scheduler (Automatisations 24/7)  |
               +─────────────────────────┬─────────────────────────+
                                         │
                                         ▼ (HTTPS / Webhook direct)
               +───────────────────────────────────────────────────+
               |             HUB_ENGINE (Google Cloud Run)         |
               |                                                   |
               |  🤖 Agent Coordinateur Général                    |
               |  🧠 Agent Veille IA & GitHub Trending             |
               |  🦅 Agent Veille Parapente & Vol Libre (FSVL/SHV) |
               |  ✉️ Agent Gmail (Triage, Brouillons & Newsletters)|
               +─────────────────────────┬─────────────────────────+
                                         │
                                         ▼
               +───────────────────────────────────────────────────+
               |                  SERVICES & MÉMOIRE               |
               |                                                   |
               |  📬 Boîte Gmail (alex.florentin@gmail.com)         |
               |  📚 Flux RSS / Blogs & Communautés                |
               |  📂 Mémoire Git Markdown (docs/memory/)           |
               +───────────────────────────────────────────────────+
```

---

## 🚀 Les 4 Piliers Actifs de Hub_Alex

### 1. 🤖 Agent de Veille Technologique & IA
* **Surveillance active** : Frontier Labs (OpenAI, DeepMind, Anthropic, Hugging Face), GitHub Trending IA, Simon Willison, Reddit r/LocalLLaMA, Hacker News Top Score, Techmeme.
* **Format Mobile** : Commande `/news_ia` sur Telegram (synthèse percutante avec liens sources cliquables).
* **Format Bureau / Newsletter** : Envoi automatique par e-mail au format HTML chaque **lundi à 08h00** (ou sur demande avec *« Envoie-moi la newsletter IA par mail »*).

### 2. 🦅 Agent de Veille Parapente & Vol Libre
* **Surveillance active** : FSVL/SHV Suisse, FFVL France, DHV Allemagne, Paragliding Forum, XCMag, Ziad Bassil (Dust of the Universe), Rock the Outdoor, Flybubble.
* **Format Mobile** : Commande `/news_parapente` ou `/parapente` sur Telegram.
* **Format Bureau / Newsletter** : Envoi automatique par e-mail au format HTML chaque **jeudi à 08h00** (ou sur demande avec *« Envoie-moi la newsletter parapente par mail »*).

### 3. ✉️ Agent Gmail & Communication Sécurisée
* **Génération de Brouillons (Drafts)** : Commande `/draft <consigne>` ou en langage naturel (*« Rédige un mail à Pierre pour confirmer le créneau »*). Rédige et enregistre le message dans votre boîte Gmail.
* **Règle de Sécurité Absolue** : L'agent **n'envoie JAMAIS d'e-mail à des tiers sans votre consentement**. Vous relisez et cliquez sur "Envoyer" dans Gmail.
* **Expédition Directe de Newsletters à Soi-Même** : Envoi direct des synthèses HTML vers `alex.florentin@gmail.com`.
* **Tri & Alertes d'Urgence** : Commande `/emails` pour classifier les messages non lus (*🚨 Urgent, 📋 Action requise, 📰 Information*).

### 4. 🛡️ Sécurité Maximale à 3 Verrous
* 🌐 **Sur le Web** : Google Sign-In (OAuth2 / 2FA) réservé exclusivement à `alex.florentin@gmail.com`.
* 📱 **Sur Telegram** : Whitelist stricte de votre ID utilisateur Telegram (`ALLOWED_TELEGRAM_USER_ID`).
* 🔐 **Sur l'API** : En-tête `X-API-Key` pour les appels Cloud Scheduler et scripts autorisés.

---

## 📱 Commandes Disponibles sur Telegram

| Commande | Action |
| :--- | :--- |
| **`/start`** | Menu d'accueil et statut du Hub |
| **`/news_ia`** | Synthèse instantanée de la veille IA & dépôts GitHub |
| **`/parapente`** | Synthèse instantanée de la veille Vol Libre & sorties matériel |
| **`/emails`** ou **`/inbox`** | Analyse et triage des e-mails non lus |
| **`/draft <consigne>`** | Rédige et enregistre un brouillon dans votre boîte Gmail |
| **`/briefing`** | Briefing quotidien (agenda, tâches et e-mails) |
| **Langage naturel** | Posez n'importe quelle question en français ! |

---

## 🛠️ Architecture Technique & Déploiement

* **Framework Backend** : FastAPI + PydanticAI (cascade de modèles Gemini 3.6/3.7/3.5/Flash-Latest).
* **Hébergement** : Google Cloud Run (Région `europe-west1`).
* **CI/CD** : Déploiement automatique sur `git push` via GitHub Actions ([.github/workflows/deploy_gcp.yml](.github/workflows/deploy_gcp.yml)).
* **Coût d'infrastructure** : **0 CHF / mois**.

---

## 🧪 Tests Automatisés

Pour lancer la suite de 30 tests unitaires en local :
```bash
docker compose up -d
docker exec -e PYTHONPATH=/app hub_engine pytest
```
