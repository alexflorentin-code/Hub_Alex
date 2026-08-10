# Hub_Alex (Control Center personnel)

Ce projet est votre **Control Center personnel** structuré selon une architecture **Hub-and-Spoke** (Monorepo) simplifiée, combinant la puissance locale d'Antigravity et l'autonomie d'un assistant disponible 24h/24 dans le cloud.

---

## 1. Fonctionnement Global

### 1.1 L'Orchestration locale (IDE)
* **L'Agent Coordinateur** (`.agents/rules/coordinator.md`) est votre interlocuteur par défaut dans l'IDE Antigravity. Il vous accueille, planifie vos tâches et délègue aux agents spécialisés ou au développement technique.
* **L'Agent Développeur** (`.agents/rules/developer.md`) vous assiste dans l'évolution du code du Hub.

### 1.2 L'Orchestration cloud (PAP)
* **Le Moteur Unique (hub_engine)** : Un serveur FastAPI (`projects/hub_engine`) hébergeant les agents écrits en Python (via **PydanticAI**). Il utilise une base de données **SQLite** locale et une mémoire sémantique vectorielle légère (**ChromaDB/FAISS**).
* **n8n** : Gère la plomberie (les appels d'API Microsoft/Google, la gestion des tokens de sécurité, la planification à 7h et les webhooks de votre bot Telegram).

---

## 2. Structure du Monorepo

* `.agents/` : Règles comportementales et guides pratiques (skills) pour vos agents IDE locaux.
* `docs/` : Journalisation, préférences et TODO-lists de votre organisation personnelle.
* `projects/` : Contient le code source technique (les Spokes).
  * `projects/hub_engine/` : API FastAPI, logique des agents PydanticAI et base de données SQLite.
* `docker-compose.yml` : Configuration Docker locale pour démarrer hub_engine et n8n en un clic.

---

## 3. Guide de Démarrage Rapide (Développement)

*(À compléter au fil des phases d'implémentation)*
