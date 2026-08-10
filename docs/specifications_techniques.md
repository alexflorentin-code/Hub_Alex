# Spécifications Techniques & Fonctionnelles — Hub_Alex

Ce document définit les spécifications détaillées des fonctionnalités de la Plateforme d'Automatisation Personnelle **Hub_Alex**, découpées selon la feuille de route (Roadmap).

---

## Phase 0 — Fondations, Sécurité & Déploiement

### Spécifications :
* **Docker Compose** : 
  * Un conteneur `hub_engine` exposant le port `8000`.
  * Un conteneur `n8n` exposant le port `5678`.
  * Volumes Docker nommés pour persister `/data` (contenant les fichiers `.db` de SQLite pour FastAPI et n8n) et les clés locales.
* **Sécurité & Authentification** :
  * Les communications entre n8n et `hub_engine` sont sécurisées par un token d'API fixe (`API_KEY`) transmis dans les en-têtes HTTP (`X-API-Key`).
  * Les secrets (clés d'API LLM, tokens) sont chargés via des variables d'environnement (`.env`).

---

## Phase 1 — Agent Veille

### Objectif :
Collecter, filtrer, catégoriser et résumer des flux d'actualités technologiques et personnelles de manière autonome.

### Spécifications Techniques :
* **Entrées (Sources)** :
  * Flux RSS (configurés dans n8n).
  * Liens web ou vidéos YouTube transmis manuellement via Telegram.
* **Traitement (Agent Veille)** :
  * **Scraping** : n8n récupère le contenu HTML complet des articles.
  * **Nettoyage & Filtrage** : Élimination des doublons sémantiques (via comparaison sémantique ou hachage simple).
  * **Analyse LLM (PydanticAI)** : 
    * L'agent évalue la pertinence de l'article sur une échelle de 1 à 5 en fonction des centres d'intérêt définis dans `docs/memory/preferences.md`.
    * Génération d'un résumé de 3 à 5 puces.
    * Attribution de tags thématiques.
* **Stockage** : 
  * Sauvegarde de l'article, du résumé, de la note et des tags dans SQLite.
  * Indexation du résumé dans ChromaDB pour recherche sémantique ultérieure.
* **Sorties (Notifications)** :
  * Rapport quotidien envoyé à 7h30 sur Telegram via n8n.
  * Commande Telegram `/veille` pour appeler un résumé immédiat des 5 articles les plus pertinents de la journée.

---

## Phase 2 — Agent Calendriers (Agenda)

### Objectif :
Gérer les plannings croisés (personnel et professionnel) sans exposer publiquement les détails internes.

### Spécifications Techniques :
* **Intégrations** :
  * Google Calendar (personnel).
  * Microsoft Outlook Calendar (professionnel).
* **Traitement (Agent Agenda)** :
  * n8n interroge les deux calendriers toutes les heures.
  * L'agent effectue une fusion logique des événements en mémoire.
  * **Détection des Conflits** : Identification des rendez-vous qui se chevauchent ou dont le temps de trajet estimé (via une API de cartographie optionnelle ou calcul simple) rend le déplacement impossible.
  * **Briefing Quotidien** : Synthèse de la journée sous forme de liste chronologique claire, avec mention spéciale des alertes et conflits détectés.
* **Sécurité** :
  * Aucune modification ou suppression d'événement d'agenda n'est autorisée de manière autonome. L'agent doit envoyer une proposition sur Telegram avec un bouton de validation : "Voulez-vous que je déplace le rendez-vous X à 14h ? [Oui] [Non]".

---

## Phase 3 — Agent Emails

### Objectif :
Filtrer et prioriser les courriels entrants importants et préparer des réponses automatiques prêtes à être envoyées.

### Spécifications Techniques :
* **Intégrations** :
  * API Gmail (personnel) et MS Graph API Outlook (professionnel).
* **Traitement (Agent Emails)** :
  * Récupération des e-mails non-lus.
  * **Classification de Priorité** : L'agent classe les e-mails en 3 catégories : *Urgent / Important*, *Normal*, *Newsletter/Ignorer*.
  * **Résumé** : Extraction des points clés et des actions requises (TODOs).
  * **Brouillons de Réponse (Drafts)** :
    * **Règle absolue** : L'agent n'a pas le droit d'envoyer d'e-mail directement.
    * Si un e-mail nécessite une réponse standard (ex: convenir d'un rendez-vous, accuser réception), l'agent génère la réponse et l'enregistre dans le dossier **Brouillons (Drafts)** de l'utilisateur.
    * L'utilisateur reçoit une alerte Telegram : "Brouillon de réponse créé pour l'email de X concernant Y. Prêt à l'envoi."

---

## Phase 4 — Interface Conversationnelle (Web & Telegram)

### Objectif :
Fournir un accès simple et sécurisé à l'orchestrateur depuis n'importe où.

### Spécifications Techniques :
* **Bot Telegram** :
  * Webhook configuré dans n8n vers la plateforme Telegram.
  * Gestion des commandes : `/start`, `/briefing`, `/todo`, `/veille`.
  * Support du texte libre : n8n transmet le texte à l'agent Coordinateur du `hub_engine`, qui répond en utilisant le contexte enrichi.
* **Interface Web Chat** :
  * Page unique HTML5 responsive, utilisant Tailwind CSS pour le style.
  * WebSockets ou appels API REST simples (`POST /api/v1/chat`) pour l'échange de messages en temps réel.
  * Sécurisation par mot de passe simple (Basic Auth ou Session Token) pour interdire l'accès public.

---

## Phase 5 — Mémoire Sémantique (Apprentissage)

### Objectif :
Permettre au système d'apprendre des préférences de l'utilisateur et d'ajuster son comportement.

### Spécifications Techniques :
* **Mémoire Explicite** :
  * L'utilisateur modifie directement les fichiers de préférences (`preferences.md`).
* **Mémoire Implicite & Apprentissage continu** :
  * Si l'utilisateur corrige une réponse de l'agent (ex: "Ne me résume plus les actualités sportives"), l'agent propose d'enregistrer cette règle.
  * Si validé, la règle est écrite dans la table `preferences` de SQLite et indexée dans ChromaDB.
  * Lors de chaque invocation d'agent, le module de RAG recherche les préférences et résolutions de bugs (`breakthroughs.md`) sémantiquement proches de la demande utilisateur pour ajuster le prompt système.
