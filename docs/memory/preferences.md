# Préférences Utilisateur — Hub_Alex

Ce fichier contient les préférences et les choix technologiques de l'utilisateur. Ces règles sont lues par les agents pour personnaliser leur comportement.

---

## 1. Profil & Langue
* **Nom de l'utilisateur** : Alexandre Florentin
* **Langue principale de communication** : Français (tutoiement ou vouvoiement professionnel selon le contexte, tutoiement privilégié pour le hub personnel).
* **Localisation** : Suisse.

---

## 2. Préférences Techniques (Développement)
* **Framework Backend** : Python (FastAPI).
* **Framework d'Agents** : PydanticAI (type-safe, basé sur les schémas Pydantic).
* **Base de données** : SQLite (persistance dans un fichier local simple).
* **Base de données vectorielle** : ChromaDB ou FAISS en mode embarqué (local).
* **Planification & Webhooks** : n8n (hébergé en local/Docker ou sur VPS léger).
* **Style de Code** :
  * Type hints obligatoires en Python.
  * Utilisation de Pydantic v2 pour la validation et la configuration.
  * Linting et formatage avec Ruff.

---

## 3. Préférences de Style Conversationnel
* Toujours être concis et aller droit au but.
* Fournir des explications techniques courtes et structurées en Markdown.
* Ne jamais ré-expliquer un code ou un fichier à moins que cela ne soit expressément demandé.
