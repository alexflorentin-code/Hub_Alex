# Journal des Décisions Techniques (Decision Log)

Ce document répertorie les arbitrages et choix d'architecture validés pour le projet Hub_Alex.

---

## [10/08/2026] Choix de la stack allégée (Smart & Pragmatic)

* **Décision** : Remplacer la base PostgreSQL et pgvector cloud par une base SQLite locale et ChromaDB embarqué dans le conteneur Python. Utiliser n8n comme relais API pour simplifier la plomberie d'authentification.
* **Contexte** : Le projet d'origine (PAP) prévoyait une stack de type production multi-utilisateurs lourde.
* **Justification** : Pour un usage personnel unique :
  * SQLite simplifie grandement l'administration (zéro configuration, sauvegarde facile par simple copie de fichier).
  * ChromaDB en local évite de payer un service cloud ou d'héberger un PostgreSQL vectoriel lourd.
  * n8n réduit de 80% le volume de code d'intégration à écrire et sécuriser en Python pour Microsoft Graph et Google Workspace, tout en gérant nativement le consentement OAuth2 graphique.
* **Implications** :
  * Le volume Docker doit persister le fichier de base de données SQLite.
  * Le backend `hub_engine` doit exposer des routes API simples et sécurisées par token d'API fixe pour être interrogé par n8n.
