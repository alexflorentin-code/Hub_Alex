# Walkthrough — Hub_Alex (Phase 0)

L'ensemble des livrables de la **Phase 0** a été réalisé, testé et poussé sur votre dépôt GitHub personnel : [https://github.com/alexflorentin-code/Hub_Alex](https://github.com/alexflorentin-code/Hub_Alex).

---

## 🛠️ Actions réalisées

### 1. Configuration & Liaison Git / GitHub
* **Gestion multi-comptes SSH** : Création d'une clé SSH personnelle (`id_ed25519_personal`) et modification de la configuration SSH (`~/.ssh/config`) pour utiliser l'hôte `github.com-personal`.
* **Liaison du dépôt** : Initialisation du dépôt Git dans `/Users/alexandreflorentin/Documents/Git/Hub_Alex` et configuration du remote sur `git@github.com-personal:alexflorentin-code/Hub_Alex.git`.
* **Ignorance de fichiers** : Création d'un `.gitignore` complet pour masquer les dossiers virtuels, les clés d'environnement, les caches et les fichiers SQLite de base de données.

### 2. Personnalisation & Organisation locale (IDE)
* **Manifeste d'agents** : Déclaration des rôles locaux dans `.agents/AGENTS.md` (Coordinateur et Développeur).
* **Règles locales** : Rédaction de `global.md`, `coordinator.md` et `developer.md` sous `.agents/rules/` définissant le périmètre de sécurité, le style conversationnel, et la politique de consentement.
* **Mémoire locale** : Création de `docs/memory/preferences.md`, `breakthroughs.md` et `decision_log.md` pour assurer la traçabilité des bugs et des arbitrages d'architecture.
* **Tâches et planning** : Initialisation de `docs/organization/todo.md` et `daily_schedule.md`.

### 3. Backend & Moteur d'exécution (`projects/hub_engine`)
* **requirements.txt** : Définition des dépendances (FastAPI, SQLAlchemy, PydanticAI, ChromaDB, etc.).
* **Dockerfile** : Conteneurisation de l'API.
* **Configuration** : Fichier `app/core/config.py` utilisant Pydantic Settings pour charger de manière sécurisée les secrets et clés d'API.
* **Base de données SQLite** : Fichier `app/core/database.py` initialisant la session SQLite, et `app/models/models.py` définissant les tables logiques de chat (`chat_messages`) et de journalisation des agents (`execution_logs`).
* **Agent Coordinateur PydanticAI** : Logique de l'agent dans `app/agents/coordinator.py` et gestion de l'injection dynamique du contexte local Markdown (`app/agents/helpers.py`).
* **Point d'entrée FastAPI** : Code dans `app/main.py` exposant l'API de diagnostic (`/api/v1/health`), le endpoint de chat (`/api/v1/chat`) et montant les fichiers statiques de l'interface.

### 4. Interface Conversationnelle Web
* **Interface Web (`app/static/index.html`)** : Création d'une interface de chat moderne, responsive, en mode sombre, avec effet de flou (glassmorphism), animations fluides de chargement et de messages, et affichage en temps réel du statut du système (FastAPI, SQLite, ChromaDB).

### 5. Orchestration Docker & Automatisation
* **docker-compose.yml** : Définition des services `hub_engine` et `n8n` (avec persistance des volumes et chargement automatique du fichier `.env`).
* **start.sh** : Script de démarrage automatisé (rendu exécutable) qui gère la création automatique du fichier `.env` d'exemple et lance Docker Compose en une seule commande.

---

## 🚀 Comment lancer et tester le Hub en local ?

1. Dans votre terminal, rendez-vous dans le dossier du projet :
   ```bash
   cd /Users/alexandreflorentin/Documents/Git/Hub_Alex
   ```
2. Lancez le script de démarrage :
   ```bash
   ./start.sh
   ```
   *(La première fois, le script s'arrêtera pour copier `.env.example` vers `.env` et vous invitera à y insérer vos clés API).*
3. Une fois les clés d'API renseignées dans `.env`, relancez `./start.sh`.
4. Accédez à vos services :
   * **Interface Web de Chat (Hub_Alex)** : [http://localhost:8000](http://localhost:8000)
   * **Interface d'automatisation (n8n)** : [http://localhost:5678](http://localhost:5678)
