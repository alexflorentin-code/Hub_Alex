# Guide Pas-à-Pas : Configuration Google Cloud & Bot Telegram

Ce guide vous accompagne pas-à-pas pour configurer votre projet **Google Cloud Platform (GCP)**, créer votre **Bot Telegram** et activer le **déploiement automatique CI/CD**.

---

## Étape 1 : Créer votre Bot Telegram (2 minutes)

### 1.1 Créer le bot et récupérer le token
1. Dans l'application Telegram, recherchez **`@BotFather`** (le bot officiel de Telegram avec un badge bleu).
2. Envoyez la commande : `/newbot`
3. Donnez un nom à votre bot (ex: `Alex Hub Control`).
4. Donnez un nom d'utilisateur qui se termine par `bot` (ex: `alex_hub_control_bot`).
5. **Copiez le Token API** fourni (ex: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`). C'est votre `TELEGRAM_BOT_TOKEN`.

### 1.2 Récupérer votre identifiant utilisateur Telegram unique
Pour que le bot ne réponde qu'à vous seul :
1. Dans Telegram, recherchez le bot **`@userinfobot`**.
2. Cliquez sur **Démarrer** (Start).
3. Il vous répondra avec votre profil. Copiez le numéro dans le champ **Id** (ex: `987654321`). C'est votre `ALLOWED_TELEGRAM_USER_ID`.

---

## Étape 2 : Configuration du projet Google Cloud (GCP) (5 minutes)

### 2.1 Créer un nouveau projet GCP
1. Rendez-vous sur la **[Console Google Cloud](https://console.cloud.google.com/)**.
2. Cliquez sur le sélecteur de projet en haut à gauche > **Nouveau projet**.
3. Nommez-le par exemple **`hub-alex`** et cliquez sur **Créer**.
4. Notez l'**ID du projet** (ex: `hub-alex-432100`).

### 2.2 Activer les APIs nécessaires
Dans la barre de recherche en haut, activez les 3 APIs suivantes :
* **Cloud Run API**
* **Artifact Registry API**
* **Cloud Scheduler API**

### 2.3 Créer le dépôt d'images Docker (Artifact Registry)
1. Allez dans **Artifact Registry** > **Dépôts**.
2. Cliquez sur **Créer un dépôt** :
   * Nom : **`hub-alex-repo`**
   * Format : **Docker**
   * Région : **europe-west1 (Belgique)**
3. Cliquez sur **Créer**.

### 2.4 Créer le compte de service pour GitHub Actions (CI/CD)
1. Allez dans **IAM et administration** > **Comptes de service** > **Créer un compte de service**.
2. Nom : `github-deployer` > Cliquez sur **Créer et continuer**.
3. Donnez les 3 rôles suivants :
   * **Administrateur Cloud Run** (`roles/run.admin`)
   * **Rédacteur Artifact Registry** (`roles/artifactregistry.writer`)
   * **Utilisateur de compte de service** (`roles/iam.serviceAccountUser`)
4. Cliquez sur **OK**.
5. Cliquez sur le compte de service créé > Onglet **Clés** > **Ajouter une clé** > **Créer une clé** > Format **JSON** > Téléchargez le fichier.

---

## Étape 3 : Configurer les Secrets sur GitHub (2 minutes)

Allez sur votre dépôt GitHub : **[https://github.com/alexflorentin-code/Hub_Alex](https://github.com/alexflorentin-code/Hub_Alex)** :
1. Allez dans **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
2. Ajoutez les secrets suivants :

| Nom du Secret | Description / Valeur |
| :--- | :--- |
| `GCP_PROJECT_ID` | L'ID de votre projet GCP (ex: `hub-alex-432100`) |
| `GCP_SA_KEY` | Ouvrez le fichier JSON téléchargé à l'étape 2.4 et collez **tout le contenu JSON** |
| `HUB_API_KEY` | Votre mot de passe secret (ex: `alex` ou une phrase secrète) |
| `BASIC_AUTH_USERNAME` | `alex` |
| `GEMINI_API_KEY` | Votre clé API Google Gemini (`AIzaSy...`) |
| `TELEGRAM_BOT_TOKEN` | Le jeton de votre bot Telegram (étape 1.1) |
| `ALLOWED_TELEGRAM_USER_ID` | Votre ID numérique Telegram (étape 1.2) |

---

## Étape 4 : Déploiement Automatique & Liaison Telegram

### 4.1 Lancer le premier déploiement
Faites un simple `git push` sur la branche `main` ! 
Allez dans l'onglet **Actions** sur GitHub : vous verrez le workflow construire l'image et la déployer sur Cloud Run en ~1 minute.

### 4.2 Lier le bot Telegram à Cloud Run (Activer le Webhook)
Une fois déployé, récupérez l'URL HTTPS de votre service Cloud Run (ex: `https://hub-alex-xxxx-ew.a.run.app`).

Ouvrez votre navigateur et visitez cette URL pour enregistrer le webhook auprès de Telegram :
```text
https://api.telegram.org/bot<VOTRE_TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<VOTRE_URL_CLOUD_RUN>/api/v1/telegram/webhook
```
Telegram vous répondra : `{"ok":true,"result":true,"description":"Webhook was set"}`.

🎉 **Félicitations !** Vous pouvez maintenant ouvrir votre application Telegram, envoyer un message à votre bot, et il vous répondra directement depuis Cloud Run !

---

## Étape 5 : Activer le Briefing Quotidien à 7h (Optionnel)

Dans la console Google Cloud :
1. Allez dans **Cloud Scheduler** > **Créer un job**.
2. Nom : `daily-briefing`
3. Fréquence : `0 7 * * *` (Tous les jours à 7h00)
4. Fuseau horaire : `Europe/Zurich` (ou `Europe/Paris`)
5. Cible : **HTTP**
   * URL : `https://<VOTRE_URL_CLOUD_RUN>/api/v1/briefing`
   * Méthode : **POST**
   * En-tête HTTP : `X-API-Key` avec votre mot de passe secret (`HUB_API_KEY`).
6. Cliquez sur **Créer**. Vous recevrez désormais votre briefing automatiquement chaque matin à 7h sur Telegram !
