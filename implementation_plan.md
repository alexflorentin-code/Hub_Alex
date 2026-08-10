# Projet Hub_Alex — Plateforme d'Automatisation Personnelle (PAP)

Créer un projet d'organisation personnelle global nommé **Hub_Alex** dans `/Users/alexandreflorentin/Documents/Git/Hub_Alex`. L'architecture fusionne le meilleur des deux mondes de manière pragmatique :
1. **La puissance locale et l'héritage de Hub_Fedelia** : Intégration native avec l'IDE Antigravity via des règles personnalisées (`.agents/rules/`), une gouvernance de consentement, et des fichiers de mémoire plate (`docs/memory/`).
2. **L'autonomie et l'accessibilité extérieure de la plateforme PAP** : Un backend FastAPI unique tournant 24h/24 dans le cloud (ou sur un VPS/Railway), interrogeable par une interface Web simple et un Bot Telegram, le tout rythmé par n8n pour les automatisations et les intégrations complexes (emails, calendriers).

---

## Architecture Technique Simplifiée (« Smart & Pragmatic »)

Pour éviter la lourdeur d'une infrastructure complexe (pas de base de données PostgreSQL lourde ni de serveurs frontend séparés) :

* **Base de données : SQLite**
  * Toutes les données structurées de l'application (logs, état des tâches, historique des briefings) sont stockées dans un unique fichier de base de données SQLite local au serveur.
  * **Mémoire sémantique (RAG) :** Nous utilisons une bibliothèque vectorielle Python intégrée directement au processus (ex: ChromaDB en mode local ou FAISS). Pas besoin de configurer et payer une base de données vectorielle cloud.
* **Orchestrateur & Tunnels API : n8n**
  * n8n s'occupe de toute la « plomberie » (connexion aux APIs Microsoft Graph et Google, renouvellement automatique des tokens OAuth, planification horaire, réception des messages Telegram).
  * n8n envoie les données récoltées à notre backend Python (`hub_engine`) pour que les agents prennent les décisions.
* **Backend conversationnel & Agents : FastAPI + PydanticAI**
  * Un unique serveur FastAPI (`projects/hub_engine`) héberge l'ensemble des agents.
  * Il expose des routes API privées sécurisées par token (utilisées par n8n).
  * Il sert également une page web de chat minimaliste (HTML/JS statique) hébergée directement par FastAPI, éliminant le besoin d'un serveur Next.js séparé.

---

## Structure du Projet (Monorepo)

```text
Hub_Alex/
├── .agents/                    # Règles pour l'IDE Antigravity
│   ├── rules/
│   │   ├── global.md           # Règles comportementales (sécurité, consentement)
│   │   ├── coordinator.md      # Agent Coordinateur local
│   │   └── developer.md        # Agent Développeur local
│   └── AGENTS.md               # Déclaration des agents IDE
├── docs/                       # Mémoire froide et documentation
│   ├── memory/
│   │   ├── preferences.md      # Vos choix de vie, styles de code et préférences
│   │   ├── breakthroughs.md    # Journal des résolutions de bugs complexes
│   │   └── decision_log.md     # Arbitrages techniques
│   └── organization/
│       ├── daily_schedule.md   # Planning quotidien
│       └── todo.md             # TODO-list globale personnelle
├── projects/                   # Spokes (Projets techniques)
│   └── hub_engine/             # FastAPI Backend & Agents Python
│       ├── app/
│       │   ├── core/           # Configuration (Pydantic Settings), DB (SQLite), Sécurité
│       │   ├── models/         # Modèles SQLite (SQLAlchemy)
│       │   ├── agents/         # Agents PydanticAI (Veille, Agenda, Emails, Sport)
│       │   │   ├── coordinator.py  # Agent principal qui hérite des contextes
│       │   │   └── specialists.py  # Agents spécialisés (Veille, Sport, etc.)
│       │   ├── static/         # Interface Web conversationnelle minimale (chat.html)
│       │   └── main.py         # Endpoints FastAPI et Webhooks
│       ├── requirements.txt    # FastAPI, pydantic-ai, sqlalchemy, chromadb, etc.
│       ├── Dockerfile
│       └── README.md
├── docker-compose.yml          # Lancement local complet (FastAPI + n8n + SQLite)
├── .gitignore
└── README.md                   # Guide général d'installation et d'utilisation
```

---

## Fonctionnement de l'Héritage des Connaissances

Pour reproduire la logique d'héritage de `Hub_Fedelia` dans le code Python de production :
1. **Chargement du contexte global** : Le backend FastAPI lit au démarrage les fichiers markdown de configuration (`docs/memory/preferences.md`, etc.).
2. **Injection de dépendance** : Lorsqu'un utilisateur pose une question (via Telegram ou le Web), l'agent **Coordinateur** est instancié avec ce contexte global comme instruction système.
3. **Délégation et enrichissement** : Si le Coordinateur décide de déléguer la demande à un agent spécialiste (ex: l'agent Veille), il lui transmet dynamiquement le contexte global enrichi des instructions spécifiques à la tâche courante.

---

## Plan d'Implémentation (Phase 0)

### Étape 1 : Initialisation Git et Liaison GitHub (Fait)
* Dépôt local initialisé dans `/Users/alexandreflorentin/Documents/Git/Hub_Alex`.
* Liaison distante configurée vers `git@github.com-fedelia:AlexFedelia/Hub_Alex.git` (en attente de la création du repo vide sur votre compte GitHub).

### Étape 2 : Initialisation de l'arborescence et des règles locales
* Créer les répertoires `.agents/rules/` et `docs/`.
* Rédiger les fichiers markdown globaux et locaux adaptés à votre contexte personnel.

### Étape 3 : Création du Backend `hub_engine` (FastAPI + SQLite + RAG local)
* Initialiser `projects/hub_engine/` et écrire les fichiers de base (FastAPI, configuration SQLite, connexion DB).
* Importer ChromaDB ou FAISS pour le RAG de mémoire sémantique.
* Écrire la structure des agents PydanticAI avec la gestion de l'héritage des contextes.

### Étape 4 : Conteneurisation et Configuration Docker Compose (avec n8n)
* Créer le fichier `Dockerfile` pour `hub_engine`.
* Rédiger un fichier `docker-compose.yml` intégrant à la fois le conteneur Python `hub_engine` et une instance `n8n` (avec base SQLite persistée localement).

---

## Plan de Vérification

### Tests automatisés locaux
* Exécution de `docker compose up --build` pour démarrer n8n et hub_engine.
* Vérification des endpoints FastAPI de diagnostic.

### Vérification manuelle
* Lancement d'un appel API pour valider la réponse d'un agent PydanticAI.
* Connexion de n8n à l'API locale.
