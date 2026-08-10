# Architecture Technique — Hub_Alex

Ce document décrit l'architecture globale, les composants techniques et les principes directeurs de la Plateforme d'Automatisation Personnelle **Hub_Alex**.

---

## 1. Philosophie & Principes Directeurs

Le système est conçu selon une architecture **Hub-and-Spoke (Monorepo)**, qui sépare clairement les règles d'organisation locales, le moteur d'exécution et les automatisations externes.

### Principes Clés :
* **Pragmatisme & Coût minimal** : Pas de base de données PostgreSQL lourde ni d'infrastructures complexes. Le système utilise des technologies légères (SQLite, ChromaDB/FAISS local) pour tourner sur un serveur à moins de 5 CHF/mois.
* **Sécurité & Consentement** : Les agents ont interdiction d'effectuer des modifications destructrices ou des envois directs d'emails sans approbation explicite. Les emails sortants sont stockés en tant que Brouillons (Drafts).
* **Découplage Fort** : Les agents ne communiquent jamais en direct. Ils passent par l'orchestrateur (l'Agent Coordinateur) qui gère la distribution des tâches et la fusion des contextes.
* **Héritage des Connaissances** : Les agents spécialisés héritent dynamiquement des préférences de l'utilisateur et des résolutions de bugs consignées localement.

---

## 2. Diagramme d'Architecture

```text
               +-----------------------------------+
               |            Utilisateur            |
               +-----------------------------------+
                  /                             \
    (Daily Email / Chat Web)             (Chat Telegram)
                /                                 \
   +-----------------------+              +-----------------------+
   |   Interface Web       |              |   Telegram App        |
   |   (Statique FastAPI)  |              +-----------------------+
   +-----------------------+                          | (Webhooks)
               \                                      v
                \                         +-----------------------+
                 \                        |          n8n          |
                  \                       |  (Relais d'APIs &     |
                   \                      |   Planificateur 7h)   |
                    \                     +-----------------------+
                     \                                |
                      \                               | (Appels API)
                       v                              v
               +----------------------------------------------+
               |        hub_engine (FastAPI Backend)          |
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
               |   Base SQLite   |            |    ChromaDB     |
               | (Données logiques)           | (Mémoire RAG)   |
               +-----------------+            +-----------------+
```

---

## 3. Composants Techniques

### 3.1 Le Hub (Local)
* **Personnalisation IDE (`.agents/`)** : Contient les règles comportementales utilisées par l'agent local d'Antigravity pour nous aider à maintenir et coder le Hub.
* **Mémoire Froide (`docs/memory/`)** : Fichiers Markdown (`preferences.md`, `breakthroughs.md`) qui servent de source de vérité pour le contexte utilisateur. Ils sont versionnés et modifiables directement par l'utilisateur.

### 3.2 Le Spoke Backend (`projects/hub_engine`)
* **Framework Web** : **FastAPI (Python)**. Il expose les points d'entrée des agents et distribue les requêtes.
* **Framework d'Agents** : **PydanticAI**. Permet d'écrire des agents typés, robustes, utilisant les modèles de langage (LLM) avec gestion fine des outils et de l'injection de dépendances.
* **Base de données relationnelle** : **SQLite**. Un fichier unique `hub.db` gère les utilisateurs, le journal d'exécution des agents, l'état des tâches et l'historique des discussions.
* **Base de données vectorielle** : **ChromaDB** ou **FAISS** (embarqué en local). Il indexe sémantiquement les documents (articles de veille, résumés d'emails) pour le RAG.
* **Interface Web intégrée** : Une page web unique (`index.html` avec Vanilla JS/Tailwind CSS via CDN) est servie directement par FastAPI via `StaticFiles`. Cela évite la lourdeur d'un serveur Next.js séparé pour un simple besoin de chat.

### 3.3 Le Spoke n8n (Planification & APIs)
* **Rôle** : n8n sert de gestionnaire de flux et de connexion aux applications tierces.
* **Intégrations** :
  * **Microsoft Graph API** : Lecture d'Outlook et Microsoft To Do. Gestion de l'authentification OAuth2 facilitée par l'interface graphique de n8n.
  * **Google Calendar API** : Lecture et écriture d'événements.
  * **Telegram Bot API** : Réception des commandes et envoi des briefings.
* **Flux de travail type** :
  1. À 7h00, n8n s'éveille et appelle les APIs Outlook/Google Calendar.
  2. n8n envoie les données brutes à `hub_engine/api/v1/briefing`.
  3. L'agent Coordinateur génère la synthèse en chargeant le contexte local de l'utilisateur.
  4. Le backend répond à n8n avec le briefing rédigé.
  5. n8n envoie ce message au format Markdown à votre bot Telegram.

---

## 4. Héritage des Connaissances (Contexte imbriqué)

Afin qu'un agent en production se comporte avec la même sensibilité que l'agent local dans l'IDE :
1. **Initialisation** : Au démarrage du backend, les fichiers Markdown de `docs/memory/` sont lus et chargés en mémoire.
2. **Context Engine** : Un module utilitaire injecte ces informations dans le `system_prompt` de base de chaque agent instancié.
3. **Hierarchy Mapping** :
   * **Niveau 0** : Règles de sécurité globales (`global.md`) + Préférences utilisateur (`preferences.md`).
   * **Niveau 1** : Objectifs de l'agent Coordinateur (`coordinator.md`).
   * **Niveau 2** : Instructions spécifiques transmises par le Coordinateur à l'agent Spécialiste.

---

## 5. Déploiement & Containerisation

Le projet est configuré avec un fichier `docker-compose.yml` qui instancie :
1. Le conteneur du backend Python (`hub_engine`).
2. Le conteneur de `n8n` configuré pour utiliser une base de données SQLite persistée.
3. Un volume partagé pour stocker de manière sécurisée les fichiers de base de données.

L'ensemble peut être déployé en un clic sur des plateformes comme **Railway**, **Render**, ou sur un **VPS** personnel léger sous Debian/Ubuntu avec Docker installé.
