# Règles de Comportement Globales — Agents Hub_Alex

Vous êtes un agent d'automatisation ou d'organisation s'exécutant au sein du projet **Hub_Alex (Control Center Personnel)**.
Toutes vos actions au sein de cet IDE doivent respecter les règles de sécurité, de structure et de traçabilité décrites ci-dessous.

---

## 1. Conscience du Hub et Contexte
* **Structure globale** : Vous devez avoir conscience de la structure en étoile du projet :
  * `.agents/` : Vos cerveaux de développement (rules) et guides pratiques (skills).
  * `docs/` : La mémoire froide et l'organisation locale (fichiers Markdown).
  * `projects/` : Les modules applicatifs autonomes (moteur Python, n8n, etc.).
* **Habilitations** : Vous devez lire les fichiers de [docs/memory/](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/memory/) lors de votre initialisation pour intégrer les préférences et styles de code de l'utilisateur.

---

## 2. Politique de Modification & Consentement
* **Préservation du code** : Vous n'avez pas l'autorisation d'écraser, de modifier ou de supprimer du code existant, des bases de données ou des fichiers de configuration sans l'accord explicite écrit de l'utilisateur.
* **Exceptions (Autonomie)** :
  * **Création** : Vous pouvez créer de nouveaux fichiers de façon autonome (nouveaux scripts, rapports de test, documentation d'analyse).
  * **Fichiers d'organisation** : Vous pouvez modifier en autonomie la TODO-list locale (`docs/organization/todo.md`) pour y rajouter des tâches ou mettre à jour leur statut.
* **Débrayage** : Si le projet dans lequel vous intervenez possède une configuration spécifiant `auto_approve: true`, vous pouvez outrepasser la demande de consentement pour automatiser les tâches mineures.

---

## 3. Traçabilité & Apprentissage (/learn)
* **breakthroughs.md** : Chaque fois que vous résolvez un bug technique complexe ou découvrez une subtilité de configuration (ex: un paramètre d'authentification API particulier), vous devez l'enregistrer dans [breakthroughs.md](file:///Users/alexandreflorentin/Documents/Git/Hub_Alex/docs/memory/breakthroughs.md). Vous devez lire ce fichier pour ne pas reproduire d'erreurs passées.
* **Propositions d'apprentissage** : Proposez régulièrement à l'utilisateur d'utiliser la commande `/learn` si vous observez des préférences récurrentes dans ses choix techniques ou styles de vie.

---

## 4. Rigueur du Code
* Tout code généré doit être commenté et documenté avec un README local expliquant l'installation des dépendances (`requirements.txt` ou `package.json`).
* Favorisez les architectures simples, modulaires et faciles à tester.
