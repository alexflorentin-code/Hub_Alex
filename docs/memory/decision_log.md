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

---

## [16/08/2026] Refonte et Automatisation de la Boîte Gmail (Inbox Zero & Triage IA)

* **Décision** : Mise en place d'un système à double niveau :
  1. *Niveau 1 (Structure Gmail)* : Découpage en 7 libellés thématiques (`0. @Action`, `1. @Attente`, `2. @Lecture`, `3. @Administratif`, `4. @Emploi & Réseau`, `5. @Hub_Alex`, `6. @Finance & Investissement`, `Personnel/Parapente`, `Personnel/IncaMail`) et filtres de délestage automatique hors de l'INBOX.
  2. *Niveau 2 (Agent IA Hub_Alex)* : Traitement via `email_agent.py` et envoi de synthèses quotidiennes et alertes urgentes sur Telegram avec pré-génération de brouillons sécurisés.
* **Résultats obtenus** :
  * Réduction du volume INBOX de 10 306 à 777 e-mails récents.
  * Réduction des non-lus de 270 à 28 e-mails réels.
  * Archivage et classement rétroactif de plus de 9 520 e-mails via script Python IMAP batch (`gmail_filter_runner.py`).
* **Documentation associée** :
  * Guide de gestion & bonnes pratiques : [gmail_inbox_zero.md](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/process_guides/gmail_inbox_zero.md)
  * Fichier de filtres exportables : [gmail_filters.xml](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/organization/gmail_filters.xml)
