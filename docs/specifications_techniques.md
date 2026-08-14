# Spécifications Techniques & Fonctionnelles — Hub_Alex (GCP Native)

Ce document définit les spécifications détaillées des fonctionnalités de **Hub_Alex** déployé sur Google Cloud Platform.

---

## 1. Sécurité & Authentification (Les 3 Verrous)

### Verrou 1 : Interface Web (HTTP Basic Auth)
* **Route protégée** : `GET /` et fichiers `/static/*`.
* **Identifiants** : Nom d'utilisateur `alex` et mot de passe correspondant à la variable `API_KEY`.
* **Comportement** : Renvoie un statut HTTP 401 avec en-tête `WWW-Authenticate: Basic` si non authentifié.

### Verrou 2 : API & Cron (X-API-Key)
* **Routes protégées** : `POST /api/v1/chat`, `POST /api/v1/briefing`.
* **Comportement** : Exige l'en-tête `X-API-Key: <valeur_de_API_KEY>`.

### Verrou 3 : Bot Telegram (Filtrage Whitelist)
* **Route** : `POST /api/v1/telegram/webhook`.
* **Filtrage** : Extraction du champ `message.from.id`. Si ce numéro est différent de `ALLOWED_TELEGRAM_USER_ID`, la requête est ignorée avec un log d'alerte.

---

## 2. Spécifications du Webhook Telegram

1. L'utilisateur envoie un message au bot Telegram.
2. Les serveurs de Telegram appellent en HTTPS : `https://<url-cloud-run>/api/v1/telegram/webhook`.
3. Le backend :
   * Valide l'ID utilisateur.
   * Transmet le texte à `run_coordinator()`.
   * Envoie la réponse au format Markdown à Telegram via `https://api.telegram.org/bot<TOKEN>/sendMessage`.

---

## 3. Spécifications du Briefing Automatique (Cloud Scheduler)

* **Fréquence** : Tous les jours à 7h00 du matin (Fuseau horaire : `Europe/Zurich` ou `Europe/Paris`).
* **Requête** : `POST https://<url-cloud-run>/api/v1/briefing` avec l'en-tête `X-API-Key: <clé>`.
* **Action** : Le coordinateur génère le briefing et l'envoie immédiatement sur Telegram sous le titre : `🌅 Briefing Quotidien Hub_Alex`.
