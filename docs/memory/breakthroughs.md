# Journal des Résolutions Complexes (Breakthroughs)

Ce journal répertorie les résolutions de bugs complexes et les apprentissages clés du projet. Les agents lisent ce document pour éviter de répéter des erreurs passées.

---

## 1. [10/08/2026] Gestion de l'Authentification Git Multi-comptes
* **Problème** : La commande `git push` échouait avec une erreur d'accès refusé (`denied to AlexFedelia`) car la clé SSH par défaut sur la machine était liée au compte professionnel, bloquant l'accès au dépôt personnel `alexflorentin-code/Hub_Alex`.
* **Résolution** :
  1. Génération d'une clé SSH dédiée : `ssh-keygen -t ed25519 -C "alex.florentin@gmail.com" -f ~/.ssh/id_ed25519_personal -N ""`.
  2. Configuration d'un alias d'hôte dans `~/.ssh/config` :
     ```text
     Host github.com-personal
         HostName github.com
         User git
         IdentityFile ~/.ssh/id_ed25519_personal
         IdentitiesOnly yes
     ```
  3. Modification de l'adresse de dépôt distante (remote URL) du projet local pour utiliser cet alias : `git remote set-url origin git@github.com-personal:alexflorentin-code/Hub_Alex.git`.
  4. Ajout de la clé publique sur le compte GitHub `alexflorentin-code`.
* **Leçon** : Toujours utiliser `git@github.com-personal` pour les commandes Git sur ce dépôt personnel pour forcer l'usage de la bonne identité SSH.
